## Description

`img.py` is a tool written in Python 3 that converts images in common formats such as **PNG** or **JPEG** into formats usable in programming projects for the **Amstrad CPC**. The output formats include:

- Pure binary files (`bin`)
- Source files in **C/C++** (`c`)
- Assembly code for **Abasm** (compatible with **WinAPE/MAXAM**) (`asm`)
- **SCN** files for loading screens (`scn`)

The output file will have the same name as the input image but with the appropriate extension for the chosen output format.

The tool also adjusts the image based on the output format and the Amstrad CPC video mode. In the case of **SCN** files, the image is automatically scaled to the correct resolution, and the color palette is calculated by selecting the most dominant colors in the image and approximating them to the nearest colors available in the Amstrad CPC palette.

### Amstrad CPC Video Modes:

- **Mode 0**: 160x200 pixels, 16 colors
- **Mode 1**: 320x200 pixels, 4 colors
- **Mode 2**: 640x200 pixels, 2 colors

## Installation

To use this tool, you need to have **Python 3.x** installed on your system. Additionally, `img.py` uses the **Pillow** image library, which can be easily installed using `pip`, the Python package manager, with the following command:

```bash
pip install pillow
```

## Basic Usage

The tool runs from the command line, taking an image file (PNG, JPEG, etc.) as input and converting it to the specified format.

```bash
python img.py <inimg> [--name NAME] [--format FORMAT] [--mode MODE]
```

### Available Options

- **`<inimg>`**: (Required) The input image file. This can be a PNG, JPEG, or other supported format.
- **`--name`**: (Optional) The reference name for the converted image. If not specified, the input file name will be used. This name is used to generate the labels or variables that reference the image in the generated code (C/C++ and ASM options).
- **`--format`**: (Optional) The output format. Valid values are `bin`, `c`, `asm`, `scn`. The default value is `bin`.
- **`--mode`**: (Optional) The Amstrad CPC graphic mode. Possible values are `0`, `1`, `2`. The default value is `0`.

## Usage Examples

1. **Convert a PNG image to a binary file without AMSDOS header (default format):**

```bash
python img.py imagen.png
```

This command converts `imagen.png` into a binary file (`imagen.bin`) without AMSDOS header, using graphic mode 0 with 16 colors.

2. **Convert a JPEG image to assembly compatible with WinAPE/MAXAM:**

```bash
python img.py imagen.jpg --format asm --mode 1
```

This command converts `imagen.jpg` into an assembly file (`imagen.asm`) ready for use in graphic mode 1 of the Amstrad CPC.

3. **Convert a PNG image to a C source file for SDCC:**

```bash
python img.py imagen.png --format c --name mi_sprite
```

This command converts `imagen.png` into C source files (`mi_sprite.h` and `mi_sprite.c`) that can be used with the SDCC compiler. The name `mi_sprite` will be used for the variables in the generated code.

4. **Convert an image to an SCN file for loading screens:**

```bash
python img.py portada.png --format scn
```

This command converts `portada.png` into an SCN file (`portada.scn`) for use as a loading screen. The image will be scaled to a resolution of 160x200 (graphic mode 0) with a maximum of 16 colors.

## License

`img.py` is free software; you can redistribute it and/or modify it under the terms of the **GNU General Public License v3**, as published by the **Free Software Foundation**.

`img.py` is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**; without even the implied warranty of **MERCHANTABILITY** or **FITNESS FOR A PARTICULAR PURPOSE**. See the **GNU General Public License** for more details.
