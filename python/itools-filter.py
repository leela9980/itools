#!/usr/bin/env python3

"""filter.py module description.

Runs generic image transformation on input images.
"""
# https://docs.opencv.org/3.4/d4/d61/tutorial_warp_affine.html


import argparse
import cv2
import itertools
import numpy as np
import os
import sys


DEFAULT_NOISE_LEVEL = 50

FILTER_CHOICES = {
    "help": "show help options",
    "copy": "copy input to output",
    "gray": "convert image to GRAY scale",
    "xchroma": "swap chromas",
    "noise": "add noise",
    "diff": "diff 2 frames",
    "compose": "compose 2 frames",
    "match": "match 2 frames (needle and haystack problem -- only shift)",
    "affine": "run an affine transformation (defined as 2x matrices A and B) on the input",
}

default_values = {
    "debug": 0,
    "dry_run": False,
    "filter": "help",
    "noise_level": DEFAULT_NOISE_LEVEL,
    "x": 10,
    "y": 20,
    "width": 0,
    "height": 0,
    "a00": 1,
    "a01": 0,
    "a10": 0,
    "a11": 1,
    "b00": 0,
    "b10": 0,
    "infile": None,
    "infile2": None,
    "outfile": None,
}


def image_to_gray(infile, outfile, debug):
    # load the input image
    inimg = cv2.imread(cv2.samples.findFile(infile))
    # convert to gray
    tmpimg = cv2.cvtColor(inimg, cv2.COLOR_BGR2GRAY)
    outimg = cv2.cvtColor(tmpimg, cv2.COLOR_GRAY2BGR)
    # store the output image
    cv2.imwrite(outfile, outimg)


def swap_xchroma(infile, outfile, debug):
    # load the input image
    inimg = cv2.imread(cv2.samples.findFile(infile))
    # swap chromas
    yuvimg = cv2.cvtColor(inimg, cv2.COLOR_BGR2YCrCb)
    yuvimg = yuvimg[:, :, [0, 2, 1]]
    outimg = cv2.cvtColor(yuvimg, cv2.COLOR_YCrCb2BGR)
    # store the output image
    cv2.imwrite(outfile, outimg)


def add_noise(infile, outfile, noise_level, debug):
    # load the input image
    inimg = cv2.imread(cv2.samples.findFile(infile))
    # convert to gray
    noiseimg = np.random.randint(
        -noise_level, noise_level, size=inimg.shape, dtype=np.int16
    )
    outimg = inimg + noiseimg
    outimg[outimg > np.iinfo(np.uint8).max] = np.iinfo(np.uint8).max
    outimg[outimg < np.iinfo(np.uint8).min] = np.iinfo(np.uint8).min
    outimg = outimg.astype(np.uint8)
    # store the output image
    cv2.imwrite(outfile, outimg)


def diff_images(infile1, infile2, outfile, debug):
    # load the input images
    inimg1 = cv2.imread(cv2.samples.findFile(infile1))
    inimg2 = cv2.imread(cv2.samples.findFile(infile2))
    # diff them
    diffimg = np.absolute(inimg1.astype(np.int16) - inimg2.astype(np.int16)).astype(
        np.uint8
    )
    # diff them
    # remove the color components
    tmpimg = cv2.cvtColor(diffimg, cv2.COLOR_BGR2GRAY)
    outimg = cv2.cvtColor(tmpimg, cv2.COLOR_GRAY2BGR)
    # reverse the colors, so darker means more change
    outimg = 255 - outimg
    # store the output image
    cv2.imwrite(outfile, outimg)


# composes infile2 on top of infile1, at (xloc, yloc)
# uses alpha
def compose_images(infile1, infile2, xloc, yloc, outfile, debug):
    # load the input images
    inimg1 = cv2.imread(cv2.samples.findFile(infile1))
    inimg2 = cv2.imread(cv2.samples.findFile(infile2), cv2.IMREAD_UNCHANGED)
    # compose them
    width1, height1, _ = inimg1.shape
    width2, height2, _ = inimg2.shape
    assert xloc + width2 < width1
    assert yloc + height2 < height1
    if inimg2.shape[2] == 3:
        # no alpha channel: just use 50% ((im1 + im2) / 2)
        outimg = inimg1.astype(np.int16)
        outimg[yloc : yloc + height2, xloc : xloc + width2] += inimg2
        outimg[yloc : yloc + height2, xloc : xloc + width2] /= 2

    elif inimg2.shape[2] == 4:
        outimg = inimg1.astype(np.int16)
        # TODO(chema): replace this loop with alpha-channel line
        for (x2, y2) in itertools.product(range(width2), range(height2)):
            x1 = xloc + x2
            y1 = yloc + y2
            alpha_value = inimg2[y2][x2][3] / 256
            outimg[y1][x1] = np.rint(
                outimg[y1][x1] * (1 - alpha_value) + inimg2[y2][x2][:3] * alpha_value
            )

    # store the output image
    outimg = outimg.astype(np.uint8)
    cv2.imwrite(outfile, outimg)


def match_images(infile1, infile2, outfile, debug):
    # load the input images
    inimg1 = cv2.imread(cv2.samples.findFile(infile1))
    inimg2 = cv2.imread(cv2.samples.findFile(infile2), cv2.IMREAD_UNCHANGED)
    # we will do gray correlation image matching: Use only the lumas
    luma1 = cv2.cvtColor(inimg1, cv2.COLOR_BGR2GRAY)
    luma2 = cv2.cvtColor(inimg2, cv2.COLOR_BGR2GRAY)
    # support needles with alpha channels
    if inimg2.shape[2] == 3:
        # no alpha channel: just use the luma for the search
        pass
    elif inimg2.shape[2] == 4:
        # alpha channel: add noise to the non-alpha channel parts
        # https://stackoverflow.com/a/20461136
        # TODO(chema): replace random-composed luma with alpha-channel-based
        # matchTemplate() function.
        luma2rand = np.random.randint(256, size=luma2.shape).astype(np.int16)
        width2, height2 = luma2.shape
        alpha_channel2 = inimg2[:, :, 3]
        # TODO(chema): replace this loop with alpha-channel line
        for (x2, y2) in itertools.product(range(width2), range(height2)):
            alpha_value = alpha_channel2[y2][x2] / 256
            luma2rand[y2][x2] = np.rint(
                luma2rand[y2][x2] * (1 - alpha_value) + luma2[y2][x2] * alpha_value
            )
        luma2 = luma2rand.astype(np.uint8)
    # match infile2 (template, needle) in infile1 (image, haystack)
    # Note that matchTemplate() does not support rotation or scaling
    # https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html
    match = cv2.matchTemplate(luma1, luma2, cv2.TM_CCOEFF_NORMED)
    # get the location for the highest match[] value
    y0, x0 = np.unravel_index(match.argsort(axis=None)[-1], match.shape)
    if debug > 0:
        print(f"{x0 = } {y0 = }")
    # prepare the output
    outimg = inimg1.astype(np.int16)
    xwidth, ywidth, _ = inimg2.shape
    x1, y1 = x0 + xwidth, y0 + ywidth
    # substract the needle from the haystack
    # this replaces black with black: Not very useful
    # outimg[y0:y1, x0:x1] -= inimg2[:,:,:3]
    # add an X in the origin (0,0) point
    # cv2.line(outimg, (0, 0), (2, 2), color=(0,0,0), thickness=1)
    # add an X in the (x0, y0) point
    # cv2.line(outimg, (x0 - 2, y0 - 2), (x0 + 2, y0 + 2), color=(0, 0, 0), thickness=1)
    # cv2.line(outimg, (x0 + 2, y0 - 2), (x0 - 2, y0 + 2), color=(0, 0, 0), thickness=1)
    # add a square in the full needle location
    cv2.rectangle(outimg, (x0, y0), (x1, y1), color=(0, 0, 0), thickness=1)

    # store the output image
    outimg = np.absolute(outimg).astype(np.uint8)
    cv2.imwrite(outfile, outimg)


def affine_transformation_matrix(
    infile, outfile, width, height, a00, a01, a10, a11, b00, b10, debug
):
    # load the input image
    inimg = cv2.imread(cv2.samples.findFile(infile))
    # process the image
    m0 = [a00, a01, b00]
    m1 = [a10, a11, b10]
    transform_matrix = np.array([m0, m1]).astype(np.float32)
    if debug > 0:
        print(f"{transform_matrix = }")
    width = width if width != 0 else inimg.shape[1]
    height = height if height != 0 else inimg.shape[0]
    outimg = cv2.warpAffine(inimg, transform_matrix, (width, height))
    # store the output image
    cv2.imwrite(outfile, outimg)


def get_options(argv):
    """Generic option parser.

    Args:
        argv: list containing arguments

    Returns:
        Namespace - An argparse.ArgumentParser-generated option object
    """
    # init parser
    # usage = 'usage: %prog [options] arg1 arg2'
    # parser = argparse.OptionParser(usage=usage)
    # parser.print_help() to get argparse.usage (large help)
    # parser.print_usage() to get argparse.usage (just usage line)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        dest="version",
        default=False,
        help="Print version",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="count",
        dest="debug",
        default=default_values["debug"],
        help="Increase verbosity (use multiple times for more)",
    )
    parser.add_argument(
        "--quiet",
        action="store_const",
        dest="debug",
        const=-1,
        help="Zero verbosity",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=default_values["dry_run"],
        help="Dry run",
    )
    parser.add_argument(
        "--noise-level",
        action="store",
        type=int,
        dest="noise_level",
        default=default_values["noise_level"],
        help="Noise Level",
    )
    parser.add_argument(
        "-x",
        action="store",
        type=int,
        dest="x",
        default=default_values["x"],
        help="Composition X Coordinate",
    )
    parser.add_argument(
        "-y",
        action="store",
        type=int,
        dest="y",
        default=default_values["y"],
        help="Composition Y Coordinate",
    )
    parser.add_argument(
        "--width",
        action="store",
        type=int,
        dest="width",
        default=default_values["width"],
        help="Output Width",
    )
    parser.add_argument(
        "--height",
        action="store",
        type=int,
        dest="height",
        default=default_values["height"],
        help="Output height",
    )
    parser.add_argument(
        "--a00",
        action="store",
        type=float,
        dest="a00",
        default=default_values["a00"],
        metavar="a00",
        help=("a00 (default: %i)" % default_values["a00"]),
    )
    parser.add_argument(
        "--a01",
        action="store",
        type=float,
        dest="a01",
        default=default_values["a01"],
        metavar="a01",
        help=("a01 (default: %i)" % default_values["a01"]),
    )
    parser.add_argument(
        "--a10",
        action="store",
        type=float,
        dest="a10",
        default=default_values["a10"],
        metavar="a10",
        help=("a10 (default: %i)" % default_values["a10"]),
    )
    parser.add_argument(
        "--a11",
        action="store",
        type=float,
        dest="a11",
        default=default_values["a11"],
        metavar="a11",
        help=("a11 (default: %i)" % default_values["a11"]),
    )
    parser.add_argument(
        "--b00",
        action="store",
        type=float,
        dest="b00",
        default=default_values["b00"],
        metavar="b00",
        help=("b00 (default: %i)" % default_values["b00"]),
    )
    parser.add_argument(
        "--b10",
        action="store",
        type=float,
        dest="b10",
        default=default_values["b10"],
        metavar="b10",
        help=("b10 (default: %i)" % default_values["b10"]),
    )
    parser.add_argument(
        "--filter",
        action="store",
        type=str,
        dest="filter",
        default=default_values["filter"],
        choices=FILTER_CHOICES.keys(),
        metavar="{%s}" % (" | ".join("{}".format(k) for k in FILTER_CHOICES.keys())),
        help="%s"
        % (" | ".join("{}: {}".format(k, v) for k, v in FILTER_CHOICES.items())),
    )
    parser.add_argument(
        "infile",
        type=str,
        nargs="?",
        default=default_values["infile"],
        metavar="input-file",
        help="input file",
    )
    parser.add_argument(
        "-i",
        "--infile2",
        action="store",
        type=str,
        dest="infile2",
        default=default_values["infile2"],
        metavar="input-file2",
        help="input file 2",
    )
    parser.add_argument(
        "outfile",
        type=str,
        nargs="?",
        default=default_values["outfile"],
        metavar="output-file",
        help="output file",
    )
    # do the parsing
    options = parser.parse_args(argv[1:])
    if options.version:
        return options
    # implement help
    if options.filter == "help":
        parser.print_help()
        sys.exit(0)
    return options


def main(argv):
    # parse options
    options = get_options(argv)
    if options.version:
        print("version: %s" % __version__)
        sys.exit(0)

    # get infile/outfile
    if options.infile == "-":
        options.infile = "/dev/fd/0"
    if options.outfile == "-":
        options.outfile = "/dev/fd/1"
    # print results
    if options.debug > 0:
        print(options)

    if options.filter == "diff":
        outimg = diff_images(
            options.infile, options.infile2, options.outfile, options.debug
        )

    elif options.filter == "compose":
        outimg = compose_images(
            options.infile,
            options.infile2,
            options.x,
            options.y,
            options.outfile,
            options.debug,
        )

    elif options.filter == "match":
        outimg = match_images(
            options.infile, options.infile2, options.outfile, options.debug
        )

    elif options.filter == "gray":
        image_to_gray(options.infile, options.outfile, options.debug)

    elif options.filter == "xchroma":
        swap_xchroma(options.infile, options.outfile, options.debug)

    elif options.filter == "noise":
        add_noise(options.infile, options.outfile, options.noise_level, options.debug)

    elif options.filter == "affine":
        affine_transformation_matrix(
            options.infile,
            options.outfile,
            options.width,
            options.height,
            options.a00,
            options.a01,
            options.a10,
            options.a11,
            options.b00,
            options.b10,
            options.debug,
        )


if __name__ == "__main__":
    # at least the CLI program name: (CLI) execution
    main(sys.argv)
