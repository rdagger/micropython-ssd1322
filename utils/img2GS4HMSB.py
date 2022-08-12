# -*- coding: utf-8 -*-
"""Utility to convert images to GS4_HMSB format."""

from PIL import Image
from os import path
import sys


def error(msg):
    """Display error and exit."""
    print(msg)
    sys.exit(-1)


def write_bin(f, pixel_list, width):
    """Save image in GS4_HMSB format."""
    list_bytes = []
    windex = 0
    pit = iter(pixel_list)
    for pix in pit:
        pix2 = 0  # Handle case where odd pixel width
        if windex + 1 < width:
            pix2 = next(pit) // 17
        pix //= 17
        # print(pix, pix2, pix << 4 | (pix2 & 0b00001111))
        list_bytes.append(pix << 4 | (pix2 & 0b00001111))

        windex += 2
        if windex >= width:
            windex = 0
    f.write(bytearray(list_bytes))


if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        error('Please specify input file: ./img2gs4hmsb.py test.png')
    in_path = args[1]
    if not path.exists(in_path):
        error('File Not Found: ' + in_path)

    filename, ext = path.splitext(in_path)
    out_path = filename + '.gs4'
    # Open in dithered grayscale
    img = Image.open(in_path).convert('L', dither=Image.FLOYDSTEINBERG)
    pixels = list(img.getdata())
    with open(out_path, 'wb') as f:
        write_bin(f, pixels, img.width)
    print('Saved: ' + out_path)
