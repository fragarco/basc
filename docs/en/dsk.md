# dsk.py

## Description
`dsk.py` is a simple Python 3.X-based tool for creating and managing DSK files, as used in simulators and disk drive emulators for Amstrad CPC computers. It can perform various operations to work with these files, with its main focus on aiding to package programs developed on modern computers.

Currently, it only supports the single-sided data format:
- 178 KB.
- 40 tracks with 9 sectors of 512 bytes each.
- Sectors numbered from 0xC1 to 0xC9.
- File table with 64 entries.

For more information on the format, refer to the following pages:
- [Amstrad CPC Emulator Documentation](http://www.benchmarko.de/cpcemu/cpcdoc/chapter/cpcdoc7_e.html#I_FILE_STRUCTURE)
- [CPCWiki - DSK Disk Image File Format](https://www.cpcwiki.eu/index.php/Format:DSK_disk_image_file_format)
- [Sinclair Wiki - DSK Format](https://sinclair.wiki.zxnet.co.uk/wiki/DSK_format)

This tool does not overwrite existing files with the same name inside the DSK; all operations add files. Therefore, you can combine the --new option with insertion operations, allowing you to generate the same DSK file every time the command is executed.

## Basic Usage

> python dsk.py <dskfile> [options]

## Available Options

- `--new`: Creates a new empty DSK file.
- `--check`: Checks if the DSK file format is compatible with the tool.
- `--dump`: Prints DSK file format information on the standard output.
- `--cat`: Lists the contents of the DSK file on the standard output.
- `--header <entry>`: Prints the AMSDOS header for the specified file entry (starting at 0).
- `--get <entry>`: Extracts the file pointed to by the specified entry (starting at 0).
- `--put-bin <file>`: Adds a new binary file to the DSK file, generating and appending an additional AMSDOS header.
- `--put-raw <file>`: Adds a new binary file to the DSK file without creating an additional AMSDOS header.
- `--put-ascii <file>`: Adds a new ASCII file to the DSK file. The file should not include an AMSDOS header.
- `--load-addr <address>`: Initial address to load the file (default 0x4000, only used in binary files with generated AMSDOS headers).
- `--start-addr <address>`: Call address after loading the file (default 0x4000, only used in binary files with generated AMSDOS headers).
- `--help`: Displays the help on the standard output.

## Usage Examples

Create a new DSK file with a BASIC program:

> python dsk.py archivo.dsk --new --put-ascii programa.bas
 
List the contents of the DSK file to verify that our program is included:

> python dsk.py archivo.dsk --cat

Add a binary file with an assembly program to the DSK file, which should be loaded and executed at address 0x4000:

> python dsk.py --new archivo.dsk --put-bin programa.bin --load-addr 0x4000 --start-addr 0x4000
