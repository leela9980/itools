#!/usr/bin/env python3

"""itools-common.py module description.


Module that contains common code.
"""


import enum
import numpy as np
import subprocess
import sys


FFMPEG_SILENT = "ffmpeg -hide_banner -y"

CONFIG_KEY_LIST = ("qpextract_bin",)


class ProcColor(enum.Enum):
    bgr = 0
    yvu = 1
    both = 2


PROC_COLOR_LIST = list(c.name for c in ProcColor)


class ImageInfo:
    width = None
    height = None

    def __init__(self, width, height, stride=None, scanline=None):
        self.stride = stride
        self.scanline = scanline
        self.width = width
        self.height = height
        self.stride = stride
        self.scanline = scanline


def run(command, **kwargs):
    debug = kwargs.get("debug", 0)
    dry_run = kwargs.get("dry_run", False)
    env = kwargs.get("env", None)
    stdin = subprocess.PIPE if kwargs.get("stdin", False) else None
    bufsize = kwargs.get("bufsize", 0)
    universal_newlines = kwargs.get("universal_newlines", False)
    default_close_fds = True if sys.platform == "linux2" else False
    close_fds = kwargs.get("close_fds", default_close_fds)
    shell = kwargs.get("shell", type(command) in (type(""), type("")))
    if debug > 0:
        print(f"running $ {command}")
    if dry_run:
        return 0, b"stdout", b"stderr"
    p = subprocess.Popen(  # noqa: E501
        command,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=bufsize,
        universal_newlines=universal_newlines,
        env=env,
        close_fds=close_fds,
        shell=shell,
    )
    # wait for the command to terminate
    if stdin is not None:
        out, err = p.communicate(stdin)
    else:
        out, err = p.communicate()
    returncode = p.returncode
    # clean up
    del p
    # return results
    return returncode, out, err


# converts a chroma-subsampled matrix into a non-chroma subsampled one
# Algo is very simple (just dup values)
def chroma_subsample_reverse(inmatrix, colorspace):
    in_w, in_h = inmatrix.shape
    if colorspace in ("420jpeg", "420paldv", "420", "420mpeg2"):
        out_w = in_w << 1
        out_h = in_h << 1
        outmatrix = np.zeros((out_w, out_h), dtype=np.uint8)
        outmatrix[::2, ::2] = inmatrix
        outmatrix[1::2, ::2] = inmatrix
        outmatrix[::2, 1::2] = inmatrix
        outmatrix[1::2, 1::2] = inmatrix
    elif colorspace in ("422",):
        out_w = in_w << 1
        out_h = in_h
        outmatrix = np.zeros((out_w, out_h), dtype=np.uint8)
        outmatrix[::, ::2] = inmatrix
        outmatrix[::, 1::2] = inmatrix
    elif colorspace in ("444",):
        out_w = in_w
        out_h = in_h
        outmatrix = np.zeros((out_w, out_h), dtype=np.uint8)
        outmatrix = inmatrix
    return outmatrix


# converts a non-chroma-subsampled matrix into a chroma subsampled one
# Algo is very simple (just average values)
def chroma_subsample_direct(inmatrix, colorspace):
    in_w, in_h = inmatrix.shape
    if colorspace in ("420jpeg", "420paldv", "420", "420mpeg2"):
        out_w = in_w >> 1
        out_h = in_h >> 1
        outmatrix = np.zeros((out_w, out_h), dtype=np.uint16)
        outmatrix += inmatrix[::2, ::2]
        outmatrix += inmatrix[1::2, ::2]
        outmatrix += inmatrix[::2, 1::2]
        outmatrix += inmatrix[1::2, 1::2]
        outmatrix = outmatrix / 4
        outmatrix = outmatrix.astype(np.uint8)
    elif colorspace in ("422",):
        out_w = in_w >> 1
        out_h = in_h
        outmatrix = np.zeros((out_w, out_h), dtype=np.uint16)
        outmatrix += inmatrix[::, ::2]
        outmatrix += inmatrix[::, 1::2]
        outmatrix = outmatrix / 2
        outmatrix = outmatrix.astype(np.uint8)
    elif colorspace in ("444",):
        out_w = in_w
        out_h = in_h
        outmatrix = np.zeros((out_w, out_h), dtype=np.uint8)
        outmatrix = inmatrix
    return outmatrix
