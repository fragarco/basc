# cdt.py

## Description
`cdt.py` is a simple Python 3.X-based tool for creating and managing CDT files used in simulators and tape emulators for Amstrad CPC computers. It can perform various operations to work with these files, with its main focus on aiding in packaging programs developed on modern computers.

Additional information about the CDT format can be found at the following link:
- [CDT Tape Image File Format](https://www.cpcwiki.eu/index.php/Format:CDT_tape_image_file_format)

For further understanding of how information was stored on actual tapes, refer to the manual on the Amstrad CPC Firmware at the following link:
- [The Amstrad 6128 Firmware Manual](https://archive.org/details/SOFT968TheAmstrad6128FirmwareManual)

This tool does not overwrite existing files with the same name within the CDT file; all operations add files. Therefore, you can combine the `--new` option with insertion operations, allowing you to generate the same CDT file every time the command is executed.

## Basic Usage

> python cdt.py <cdtfile> [options]

## Available Options
- `--new`: Creates a new empty CDT file.
- `--check`: Checks if the CDT file format is compatible with the tool.
- `--cat`: Lists all blocks currently present in the CDT file on the standard output.
- `--put-bin <file>`: Adds a new binary/basic file to the CDT file.
- `--put-ascii <file>`: Adds a new ASCII file to the CDT file.
- `--put-raw <file>`: Adds the file directly inside a data block without any header.
- `--load-addr <address>`: Initial address to load the file.
- `--start-addr <address>`: Call address after loading the file.
- `--name <name>`: Name that will be displayed when loading the binary/ASCII file.
- `--speed <speed>`: Write speed: 0 = 1000 bauds, 1 (default) = 2000 bauds.

## Usage Examples

Create a new CDT file with a BASIC program:

> python cdt.py tape.cdt --new --put-ascii program.bas

List the blocks in the CDT file:

> python cdt.py tape.cdt --cat

Add a binary file to the CDT file that displays the name "my program" when each block is loaded:

> python cdt.py tape.cdt --put-bin program.bin --load-addr 0x8000 --start-addr 0x8000 --name "my program"
