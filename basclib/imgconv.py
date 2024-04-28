#!/usr/bin/env python

"""
IMGCONV.PY by Javier Garcia

Tool that converts regular image files to CPC images. The conversion depends
on the screen mode, that must be specified (0 by default). As reference:

Mode 2, 640×200, 2 colors
bit 7	bit 6	bit 5	bit 4	bit 3	bit 2	bit 1	bit 0
pixel 0	pixel 1	pixel 2	pixel 3	pixel 4	pixel 5	pixel 6	pixel 7

Mode 1, 320×200, 4 colors (2 bits x pixel: bit 1 then bit 0)
bit 7	bit 6	bit 5	bit 4	bit 3	bit 2	bit 1	bit 0
pixel 0 pixel 1 pixel 2 pixel 3 pixel 0 pixel 1	pixel 2 pixel 3

Modo 0, 160×200, colors (4 bits x pixel: bit 0 bit 2 bit 1 bit 3)
bit 7	bit 6	bit 5	bit 4	bit 3	bit 2	bit 1	bit 0
pixel 0 pixel 1 pixel 0 pixel 1 pixel 0 pixel 1 pixel 0 pixel 1

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation in its version 3.

This program is distributed in the hope that it will be useful
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys
import os
import argparse
from PIL import Image

# Array of CPC colours in the following format:
# index     = firmware value (1-26) as it is used in INK basic instruction
# 1st value = hardware byte value (used in assembly to set colors in the PAL chip)
# (r, g, b) = tuple with RGB (0-255) values

CPC_FW_COLORS = [
(0x14, (0, 0, 0)),          # Black
(0x04, (0, 0, 128)),        # Blue
(0x15, (0, 0, 255)),        # Bright Blue
(0x1C, (128, 0, 0)),        # Red
(0x18, (128, 0, 128)),      # Magenta
(0x1D, (128, 0, 255)),      # Mauve
(0x0C, (255, 0, 0)),        # Bright Red
(0x05, (255, 0, 128)),      # Purple
(0x0D, (255, 0, 255)),      # Bright Magenta
(0x16, (0, 128, 0)),        # Green
(0x06, (0, 128, 128)),      # Cyan
(0x17, (0, 128, 255)),      # Sky Blue
(0x1E, (128, 128, 0)),      # Yellow
(0x00, (128, 128, 128)),    # White
(0x1F, (128, 128, 255)),    # Pastel Blue
(0x0E, (255, 128, 0)),      # Orange
(0x07, (255, 128, 128)),    # Pink
(0x0F, (255, 128, 255)),    # Pastel Magenta
(0x12, (0, 255, 0)),        # Bright Green
(0x02, (0, 255, 128)),      # Sea Green
(0x13, (0, 255, 255)),      # Bright Cyan
(0x1A, (128, 255, 0)),      # Lime
(0x19, (128, 255, 128)),    # Pastel Green
(0x1B, (128, 255, 255)),    # Pastel Cyan
(0x0A, (255, 255, 0)),      # Bright Yellow
(0x03, (255, 255, 128)),    # Pastel Yellow
(0x0B, (255, 255, 255)),    # Bright White
]

# Translates from HW color value to Firmware index
CPC_HW_COLORS = {
0x14: 0, 
0x04: 1,
0x15: 2,
0x1C: 3,
0x18: 4,
0x1D: 5,
0x0C: 6,
0x05: 7,
0x0D: 8,
0x16: 9,
0x06: 10,
0x17: 11,
0x1E: 12,
0x00: 13,
0x1F: 14,
0x0E: 15,
0x07: 16,
0x0F: 17,
0x12: 18,
0x02: 19,
0x13: 20,
0x1A: 21,
0x19: 22,
0x1B: 23,
0x0A: 24,
0x03: 25,
0x0B: 26
}

CPC_RGB_COLORS = [
(0, 0, 0),          # Black
(0, 0, 128),        # Blue
(0, 0, 255),        # Bright Blue
(128, 0, 0),        # Red
(128, 0, 128),      # Magenta
(128, 0, 255),      # Mauve
(255, 0, 0),        # Bright Red
(255, 0, 128),      # Purple
(255, 0, 255),      # Bright Magenta
(0, 128, 0),        # Green
(0, 128, 128),      # Cyan
(0, 128, 255),      # Sky Blue
(128, 128, 0),      # Yellow
(128, 128, 128),    # White
(128, 128, 255),    # Pastel Blue
(255, 128, 0),      # Orange
(255, 128, 128),    # Pink
(255, 128, 255),    # Pastel Magenta
(0, 255, 0),        # Bright Green
(0, 255, 128),      # Sea Green
(0, 255, 255),      # Bright Cyan
(128, 255, 0),      # Lime
(128, 255, 128),    # Pastel Green
(128, 255, 255),    # Pastel Cyan
(255, 255, 0),      # Bright Yellow
(255, 255, 128),    # Pastel Yellow
(255, 255, 255),    # Bright White
]

class ConversionError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
    

class ImgConverter:
    def __init__(self, mode=0, palette = [0x14 for i in range(0,16)]):
        self.mode = mode
        self.palette = palette
        self.img = bytearray()
        self.imgw = 0
        self.imgh = 0
        self._check_palette(mode)
        
    def _colors_per_mode(self, mode):
        if mode == 0: return 16
        return 4 if mode == 1 else 2

    def _check_palette(self, mode):
        colors = self._colors_per_mode(mode)
        if colors < len(self.palette):
            raise ConversionError("palette has too many entries, max %d vs %d entries"%(colors, len(self.palette)))
        for color in self.palette:
            if color not in CPC_HW_COLORS:
                raise ConversionError("palette includes an unknown hardware color value: %s"%(hex(color)))

    def _palette2colors(self):
        colors = []
        for hwid in self.palette:
            fwid = CPC_HW_COLORS[hwid]
            colors.append(CPC_FW_COLORS[fwid][1])
        return colors

    def _get_color_distance(self, col1, col2):
        """ colors expected as (r, g, b) values"""
        return abs(col1[0] - col2[0]) + abs(col1[1] - col2[1]) + abs(col1[2] - col2[2])
    
    def _findcolor(self, rgbpixel, cpccolors):
        nearest = (999, -1)
        for i in range(0, len(cpccolors)):
            diff = (self._get_color_distance(rgbpixel, cpccolors[i]), i)
            nearest = min(nearest, diff)
        return nearest

    def _img2mode(self):
        pixelxbyte = 8 if self.mode == 2 else 4 if self.mode == 1 else 2
        totalbytes = int((self.imgh * self.imgw) / pixelxbyte)
        data = bytearray([0x00 for i in range(0, totalbytes)])
        for i in range(0, len(self.img)):
            byte = int(i / pixelxbyte)
            if self.mode == 2:
                pos = 7 - (i % pixelxbyte)
                data[byte] = data[byte] | (self.img[i] << pos)
            elif self.mode == 1:
                pos = 3 - (i % pixelxbyte)
                data[byte] = data[byte] | (self.img[i] & 0x02) << (pos+4) | (self.img[i] & 0x01) << pos
            else:
                pos = 1 - (i % pixelxbyte)
                data[byte] = data[byte] | \
                             (self.img[i] & 0x01) << (6 + pos) | \
                             (self.img[i] & 0x02) << (1 + pos) | \
                             (self.img[i] & 0x04) << (2 + pos) | \
                             (self.img[i] & 0x08) >> (3 - pos)
        return data

    def build_palette(self, rgbimg, mode):
        """
        Assigns each pixel in the image to the nearest CPC color. When
        all pixels are assigned, the method retains the colors with more
        assignements and builds the palette. The mode sets the max number
        of entries in the palette.
        """
        w, h = rgbimg.size
        cpccolors = [(0, i) for i in range(0, len(CPC_RGB_COLORS))]
        for y in range(0, h):
            for x in range(0, w):
                pixel = rgbimg.getpixel((x, y))
                _, colorindex = self._findcolor(pixel, CPC_RGB_COLORS)
                pixels, fwvalue = cpccolors[colorindex]
                cpccolors[colorindex] = (pixels + 1, fwvalue)
        cpccolors = list(filter(lambda item: item[0] > 0, cpccolors))
        cpccolors.sort(reverse=True)
        colors = self._colors_per_mode(mode)
        palette = list(map(lambda item: CPC_FW_COLORS[item[1]][0], cpccolors[0:colors]))
        return palette

    def build_cpcimg(self, rgbimg, mode):
        """
        Convert each RGB value to the nearest CPC HW color value included in the
        palette.
        """
        self.mode = mode
        self.palette = self.build_palette(rgbimg, mode)
        palettecolors = self._palette2colors()
        self.img = bytearray()
        self.imgw, self.imgh = rgbimg.size
        for y in range(0, self.imgh):
            for x in range(0, self.imgw):
                pixel = rgbimg.getpixel((x, y))
                _, colorindex = self._findcolor(pixel, palettecolors)
                self.img.extend(colorindex.to_bytes(1, 'little'))
        if len(self.img) != (self.imgw * self.imgh):
            raise ConversionError("CPC image size doesn't match with source image")

    def write_bin(self, target, ext='.bin', cpcimg = None):
        try:
            data = cpcimg if cpcimg != None else self._img2mode()
            with open(target + ext, 'wb') as fd:
                fd.write(data)
        except IOError as e:
            raise ConversionError("%s couldn't be create due to %s" % (target + ext, str(e)))
        paletteinfo = []
        for hw in self.palette:
            fw = CPC_HW_COLORS[hw]
            color = CPC_FW_COLORS[fw][1]
            paletteinfo.append("%d\t\t0x%02X\t"%(fw, hw) + str(color) + '\n')         
        try:
            with open(target + ext + '.inf', 'w') as fd:
                fd.writelines([
                    "FILE: %s\n" % target + ext,
                    "WIDTH: %d\n" % self.imgw,
                    "HEIGHT: %d\n" % self.imgh,
                    "MODE: %d\n" % self.mode,
                    "PALETTE COLORS: %d\n" % len(self.palette),
                    "\n",
                    "FW\t\tHW\t\tRGB\n",
                ])
                fd.writelines(paletteinfo)
        except IOError as e:
            raise ConversionError("%s.inf couldn't be create due to %s" % (target + ext, str(e)))

    def write_c(self, target):
        data = self._img2mode()
        target = target.replace('.', '_')
        targetu = target.upper()
        try:
            with open(target + '.h', 'w') as fd:
                fd.writelines([
                    "// Include file for SDCC compiler\n",
                    "// Generated automatically by pycpc-imgconv\n",
                    "\n",
                    "extern const unsigned char %s_PALETTE[%d];\n" % (targetu, len(self.palette)),
                    "extern const unsigned char %s_IMG[%d];\n" % (targetu, len(data))
                ])
            strpalette = '{ %s }' % ', '.join('0x%02X' % x for x in self.palette)
            with open(target + '.c', 'w') as fd:
                fd.writelines([
                    "// Implementation file for SDCC compiler\n",
                    "// Generated automatically by pycpc-imgconv\n",
                    "\n",
                    "// mode %d, width %d, height %d\n" % (self.mode, self.imgw, self.imgh),
                    "\n",
                    "const unsigned char %s_PALETTE[%d] = %s;\n\n" % (targetu, len(self.palette), strpalette),
                    "const unsigned char %s_IMG[%d] = {\n" % (targetu, len(data)),
                ])
                datalines = []
                pixbyte = 8 if self.mode == 2 else 4 if self.mode == 1 else 2
                row = min(16, int(self.imgw / pixbyte))
                while len(data) > 0:
                    line = data[0:row]
                    end = ',\n' if len(data) > row else '\n'
                    datalines.append('\t' + ', '.join('0x%02X' % x for x in line) + end)
                    data = data[row:]
                datalines.append('};\n')
                fd.writelines(datalines)
        except IOError as e:
            raise ConversionError("couldn't create C files due to %s" % str(e))
        
    def write_asm(self, target):
        data = self._img2mode()
        target = target.replace('.', '_')
        targetl = target.lower()
        try:
            strpalette = ', '.join('0x%02X' % x for x in self.palette)
            with open(target + '.s', 'w') as fd:
                fd.writelines([
                    ";; Assembly implementation file for ASZ80 assembler\n",
                    ";; Generated automatically by pycpc-imgconv\n",
                    "\n",
                    ";; mode %d, width %d, height %d\n" % (self.mode, self.imgw, self.imgh),
                    "\n",
                    "%s_pal::\n" % targetl,
                    ".db " + strpalette + "\n\n",
                    "%s_img::\n" % targetl,
                ])
                datalines = []
                pixbyte = 8 if self.mode == 2 else 4 if self.mode == 1 else 2
                row = min(16, int(self.imgw / pixbyte))
                while len(data) > 0:
                    line = data[0:row]
                    datalines.append('.db ' + ', '.join('0x%02X' % x for x in line) + '\n')
                    data = data[row:]
                datalines.append('\n')
                fd.writelines(datalines)
        except IOError as e:
            raise ConversionError("couldn't create asm file due to %s" % str(e))

    def write_scn(self, target):
        """ 
        Images copied to the video memory need to be interlaced:
        25 first 25 cursor lines
        25 second 25 cursor lines
        ...
        25 eigthth 25 cursor lines
        """
        requiredw = 160 if self.mode == 0 else 320 if self.mode == 1 else 640
        if self.imgw != requiredw or self.imgh != 200:
            raise ConversionError("input image must be %dx200 for mode %d" % (requiredw, self.mode))
        
        data = self._img2mode()
        interlaced = bytearray()
        # The video memory is divided in 8 blocks of 25 lines (200 lines total, 80 bytes per line):
        #   first block has all cursors first line 
        #   second block has all cursors second line
        #   ... 
        # Each block has 48 bytes of padding at the end so:
        # Line Address (0-200) = 0xC000 + ((Line / 8) * 80) + ((Line % 8) * 2048)
        padding = bytearray(0 for i in range(0,48))
        for block in range(0, 8):
            for line in range(0,25):
                offset = 80 * block
                start = (80 * 8 * line) + offset
                interlaced.extend(
                    data[start:start + 80]
                )
            interlaced.extend(padding)
        self.write_bin(target, '.scn', interlaced)

def run_read_inputimg(srcfile):
    try:
        img = Image.open(srcfile)
        return img.convert('RGB')
    except Exception as e:
        print("[pycpc-imgconv] error trying to read the input image", srcfile)
        print(str(e))
        sys.exit(1)

def run_convert(args):
    inputimg = run_read_inputimg(args.inimg)
    converter = ImgConverter()
    converter.build_cpcimg(inputimg, args.mode)
    target = args.name if args.name != '' else os.path.splitext(args.inimg)[0]
    if args.format == 'bin':
        converter.write_bin(target)
    elif args.format == 'c':
        converter.write_c(target)
    elif args.format == 'asm':
        converter.write_asm(target)
    elif args.format == 'scn':
        converter.write_scn(target)
    else:
        raise ConversionError("unkown destination format, supported formats are: bin, c, asm, bas.")

def process_args():
    parser = argparse.ArgumentParser(
        prog='imgconv.py',
        description="""
        Tool that converts regular image files (PNG, JPEG, etc.) to formats usable in
        Amstrad CPC programs:
            'bin': binary pure files without AMSDOS header.
            'c'  : C/C++ source files for use with SDCC.
            'asm': ASZ80 assembly compatible source file.
            'scn': interlaced image following the Amstrad video memory scheme.
        """
    )
    parser.add_argument('inimg', help='Input image file.')
    parser.add_argument('--name', type=str, default='', help='Name that has to be used to reference the image. If is not specified the input file name will be used.')
    parser.add_argument('--format', type=str, default='bin', help='Format to be used for the output file (bin by default).')
    parser.add_argument('--mode', type=int, default=0, help='Graphic mode (by default 0).')
    args = parser.parse_args()
    return args

def main():
    args = process_args()
    try:
        run_convert(args)
    except ConversionError as e:
        print("[pycpc-imgconv] error: " + str(e))
    sys.exit(0)

if __name__ == "__main__":
    main()