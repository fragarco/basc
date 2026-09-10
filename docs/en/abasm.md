<!-- omit in toc -->
ABASM: USER MANUAL
==================
**A Python based assembler for the Amstrad CPC machines**

- [Introduction](#introduction)
  - [Why Another Assembler for Amstrad?](#why-another-assembler-for-amstrad)
- [Basic Usage](#basic-usage)
  - [Available Options](#available-options)
  - [Usage Examples](#usage-examples)
  - [Creating a Project Using ASMPRJ](#creating-a-project-using-asmprj)
- [Assembly Output](#assembly-output)
  - [The Binary File](#the-binary-file)
  - [Program Listing](#program-listing)
  - [Symbol File](#symbol-file)
- [Syntax](#syntax)
  - [Comments](#comments)
  - [Labels](#labels)
  - [Instructions](#instructions)
  - [Libraries](#libraries)
  - [Assembler Directives](#assembler-directives)
    - [ALIGN](#align)
    - [ASSERT](#assert)
    - [DB, DM, DEFB, DEFM](#db-dm-defb-defm)
    - [DS, DEFS, RMEM](#ds-defs-rmem)
    - [DW, DEFW](#dw-defw)
    - [EQU](#equ)
    - [IF](#if)
    - [IFNOT](#ifnot)
    - [INCBIN](#incbin)
    - [MACRO](#macro)
    - [LIMIT](#limit)
    - [LET](#let)
    - [READ](#read)
    - [REPEAT](#repeat)
    - [ORG](#org)
    - [PRINT](#print)
    - [SAVE](#save)
    - [STOP](#stop)
    - [WHILE](#while)
  - [Expressions and Special Characters](#expressions-and-special-characters)
- [Libraries included in ABASM](#libraries-included-in-abasm)
  - [CPCRSLIB](#cpcrslib)
  - [CPCTELERA](#cpctelera)
- [The Z80 instruction set](#the-z80-instruction-set)
- [Changelog](#changelog)

# Introduction

ABASM is a cross-assembler specifically designed for the Amstrad CPC platform and its Z80 CPU. Developed in Python 3, its main goal is to provide a lightweight and highly portable tool for programmers interested in writing assembly code for this classic 8-bit platform. With no external libraries or third-party tools required, ABASM can run on any system with a Python 3 interpreter. Additionally, the project includes other tools, also written in Python and with no dependencies, to package the assembler’s output into DSK or CDT files for example, o to create a basic project structure (ASMPRJ).

ABASM is based on the fantastic pyZ80 project, initially created by Andrew Collier and later modified by Simon Owen.

## Why Another Assembler for Amstrad?

ABASM was conceived from the idea of having a portable tool that is easy to modify by anyone, without relying on specific operating systems or development environments. One of its goals is to provide a syntax compatible with the old MAXAM assembler, WinAPE syntax, and Virtual Machine Simulator. This gives developers several options to debug their code during development.

However, if you're looking for efficiency rather than portability and ease of modification, you may want to try the following assemblers:

* [Pasmo](https://pasmo.speccy.org/)
* [ASZ80](https://shop-pdp.net/ashtml/)
* [Rasm](https://github.com/EdouardBERGE/rasm)

# Basic Usage

To assemble a source file written in assembly language (e.g., `program.asm`), simply run the following command:

```
python3 abasm.py <program.asm> [options]
```

This command will assemble the `program.asm` file and generate a binary file with the same name, `program.bin`.

## Available Options

- `-d` or `--define`: Allows defining `SYMBOL=VALUE` pairs. These symbols can be used in the code as constants or labels. This option can be used multiple times to define several symbols.
- `--start`: Defines the memory address that will be used as the starting point for loading the program. By default, this address is `0x4000`, but it can also be set directly in the code using the `ORG` directive.
- `--tolerance`: Sets the tolerance level for deviations from strictly correct syntax (WinApe performs relatively lenient syntax checks). Accepted values: 0, 1, and 2. The default value is 0, indicating the strictest level of syntax enforcement.
- `-s` or `--sfile`: Generates a new .s file with all assembled code in one file, including the code imported from other files.
- `-o` or `--output`: Specifies the name of the output binary file. If this option is not used, the name of the input file will be used, with its extension changed to `.bin`.
- `v` or `--output`: Shows program's version and exits.
- `--verbose`: Prints more information in the console as the assemble progresses.
  
## Usage Examples

Define a constant used in the code:

```
python3 abasm.py program.asm -d MY_CONSTANT=100
```

Set the exact name of the assembled binary file:

```
python3 abasm.py program.asm -o output.bin
```

Set the starting memory address for calculating jumps and other relative references in the source code, for example to `0x2000`:

```
python3 abasm.py program.asm --start 0x2000
```

## Creating a Project Using ASMPRJ

In `ABASM`, project management is straightforward. It is sufficient to create a main assembly source file that imports any additional required files using the `READ` directive. After running `ABASM`, the assembled binary file will be generated. A subsequent call to the `DSK` or `CDT` tools is then enough to package the result for use in emulators or on real hardware (for example, via devices such as Gotek, M4, or DDI-Revival).

```bash
python3 abasm.py main.asm
python3 dsk.py -n main.dsk --put-bin main.bin --start-addr=0x4000 --load-addr=0x4000
```

It is also possible to quickly generate a basic project structure using the `ASMPRJ` tool. This utility automatically creates a build script with everything needed to get started: on Windows, a `make.bat` file is generated, while on Linux and macOS a `make.sh` file is created. In addition, a `main.asm` file containing ready-to-use example code is included.

```bash
python3 asmprj.py -n myproject
```

For more detailed information, please refer to the specific `ASMPRJ` documentation.

# Assembly Output

A successful execution of ABASM generates several files. This section provides a brief explanation of each of these outputs.

## The Binary File

The final product of the assembly process is a binary file (usually with the `.BIN` extension) that is ready to be loaded into memory and executed on an Amstrad CPC. The source code can be divided into multiple files, but only one—the main file—is passed as a parameter to ABASM to start the assembly process. Additional files are included as they are referenced by the `READ` or `INCBIN` directives.

ABASM does not generate relocatable code, meaning it assumes a fixed starting memory address. This load address can be specified as a parameter when calling ABASM or set within the main file using the `ORG` directive.

For example, the following assembly code, which loads the value `0xFF` into the first position of the video memory, would generate the binary content shown below (in hexadecimal).

```
org  0x4000       ; Set the initial memory load address

main:
    ld   a,0xFF       ; Load the value 0xFF into the accumulator
    ld   (0xC000),a   ; Load the content of A into the first byte 
                      ; of video memory
endloop:              ; Infinite loop
    jp endloop        ; The value of 'endloop' is calculated 
                      ; based on the starting address set by ORG
```

```
3E FF 32 00 C0 C3 05 40
```

Since the Z80 is *little-endian*, we can see that the last three bytes are `C3 05 40`, which corresponds to `C3 4005`—the machine code for `jp endloop`, with `endloop` calculated from the starting address `0x4000`.

## Program Listing

For the programmer’s reference, the assembly process also generates a file containing a listing of the original program along with the binary result of each instruction. This file has the `.LST` extension.

Continuing with the previous example, the generated `.LST` file would contain the following:

```
main.asm      000001  4000               	org  0x4000
main.asm      000002  4000               	main
main.asm      000003  4000  3E FF        	ld   a, 0xFF
main.asm      000004  4002  32 00 C0     	ld  (0xC000), a
main.asm      000005  4005               	endloop
main.asm      000006  4005  C3 05 40     	jp endloop
```

The first column indicates the source archive. The second column shows the sequential line number in the source code. The third column indicates the memory location where the generated code was placed (if any, since some directives and labels do not generate binary code). The fourth column displays the binary code produced by assembling the instruction, and the last column shows the original instruction.

## Symbol File

ABASM also generates a listing of all symbols and their associated values. Most of these will be labels used to mark jump points or memory locations where certain data has been stored.

The extension of this file is `.MAP`, and it is formatted as a Python dictionary. This allows the file to be used by other utilities (such as DSK and CDT packagers) and to reference the symbols rather than their actual values. An example of using this file can be found in the documentation for DSK and CDT utilities.

```
# List of symbols in Python dictionary format
# Symbol: [address, total number of reads (uses), file name]
{
	"ENDLOOP": [0x4005, 2, "MAIN.ASM"],
	"MAIN": [0x4000, 1, "MAIN.ASM"],
}
```

# Syntax

ABASM's syntax is designed to closely resemble that of the MAXAM assembler. This syntax is quite compatible with that supported by the WinAPE emulator. Additionally, ABASM supports some variations that also make it compatible with the syntax used by the Retro Virtual Machine emulator. The goal is to provide developers using ABASM with several tools for debugging and testing their programs.

Below is a simple example of a program written using ABASM syntax. This example demonstrates three of the basic elements of any assembly language program: labels, instructions, and comments. A fourth element would be assembler directives, commands directed at ABASM itself rather than at the Z80 processor. In this chapter, we will also review the complete list of supported directives.

An important aspect of all four elements is that ABASM is case-insensitive. Therefore, 'LD A,32' and 'ld a,32' produce the same result. The same applies to labels: 'main', 'MAIN', or 'Main' are considered the same label.

```
; Prints all ASCII characters between code 32 and 128.
; It's a variation of the first example presented in the
; MAXAM manual

main              ; defines the global label 'main'
    ld a,32       ; first ASCII letter code in accumulator

!loop             ; defines the local label 'loop'
    call &BB5A    ; CALL txt_output, the firmware output routine
    inc  a        ; move to next character
    cp   128      ; have we done them all?
    jr   c,!loop  ; no - go back for another one

.end  
    jp   end      ; infinite loop used as the program's end point

```

Another important aspect is that ABASM reserves the character '!' at the beginning of any label to designate local labels, which will only be accesible from within the source file where they got declared.

## Comments

Comments in assembly code are annotations written by the programmer that are not interpreted or executed by the CPU. Their purpose is to provide additional information about the code, making it more understandable and maintainable.

Comments are important in any programming language, but in assembly, they are even more crucial due to the low level of abstraction of the language. This makes the code harder to interpret. Therefore, comments are essential for explaining the purpose and functionality of the code. As a general rule, it is recommended to use comments to:

- Describe complex parts of the code, explaining what a particular sequence of instructions does or the parameters and return value of a subroutine.
- Delimit sections of the code, such as loops, functions, or logical blocks.
- Provide context, indicating the purpose of a variable, label, or constant.

In ABASM, comments are usually indicated with the character ';' (semicolon). When ABASM encounters this character, it ignores the rest of the line.

```
; This is a comment
; This is another comment
```

## Labels

Labels in assembly code are symbolic names used to mark a specific position in the program, such as a memory address or an instruction. Their main uses include:

- In jumps and loops: Labels are used as targets in jump instructions (JMP, JE, etc.), allowing the flow of execution to be redirected to a specific part of the program.

- In data definitions: Labels are used to refer to variables or data in memory, making them easier to access and manipulate.

- As entry points to code blocks: Labels help make the code more readable and maintainable by providing descriptive names to important sections of the program.

All labels are **global** by default, meaning they must be unique regardless of how many files the source code is divided into. ABASM ignores the leading '.' in label definitions to support the WinApe label declaration format.  

To create a local label (restricted to a module/file or within a macro), the label must start with the symbol '!'. If the label is defined outside a macro, it is considered a **module-local label**, accessible only within the file where it is declared. This also prevents the label from appearing in the Symbol File.  

If the label is defined inside a macro, it is treated as a **macro-local label**. Macro-local labels are essential to prevent errors caused by label redefinitions when the macro is invoked multiple times.

```
!loop
  <some other code>
  dec b
  jr z,!loop
```

## Instructions

Instructions are operations that the CPU (the Z80 processor in our case) must perform. The process of assembling involves generating the corresponding binary code for these instructions. Each instruction typically consists of an *opcode* and its *operands*.

An opcode (short for operation code) is the part of an instruction that specifies the action the CPU must perform. It is a unique binary or hexadecimal value associated with a particular operation, such as adding, subtracting, loading a value into a register, or performing a comparison. Thus, the opcode determines the operation to execute, while the operands (if any) provide the data needed for that operation. For example:

```
ld a,32
```

The *opcode* (or its nemotecnic more precisely) would be 'ld a', while the operand would be '32'. The meaning of the opcode is 'load into register A', and the value to load is the number 32.

ABASM supports all standard Z80 instructions. To enhance compatibility with WinAPE syntax, instructions like AND, CP, OR, and SUB can accept adding the A register as part of the *opcode*. However, the shorter form without the explicit A is preferred. Users can contol how this altenatives are managed (issue an error, issue a warning, acept them) thorugh the command-line option `--tolerance LEVEL'.

| Tolerance level  | Behaviour |
|------------------|-------------|
| --tolerance 0  | Default value. This is the strictest mode. Opcodes such as `SUB A`, `CP A`, etc., which are tolerated by WinApe, will result in a syntax error in ABASM. |
| --tolerance 1  | Allows alternative opcodes like `SUB A`, `CP A`, etc. These will generate a warning instead of an error, and the assembly process will continue. |
| --tolerance 2  | Fully accepts alternative opcodes. Errors due to issues like truncation —for example, using a two-byte value in a one-byte operand— will generate warnings instead of stopping the assembly. |

Regarding operands, ABASM fully supports all standard Z80 8-bit registers: A, B, C, D, E, H, and L, as well as the special 8-bit registers I and R. It also supports all standard Z80 16-bit registers: AF, BC, DE, HL, and SP, along with the index registers IX and IY. Additionally, ABASM provides support for the undocumented use of the 8-bit portions of the IX and IY registers, allowing for IXL, IXH, IYL, and IYH. The alternate AF' register is also supported for use in appropriate instructions, such as in the `EX AF, AF'` command.

Lastly, ABASM supports all standard Z80 condition flags: NZ, Z, NC, C, PO, PE, P, and M.

To learn more about each instruction, a short list can be consulted in the `Z80 Instruction Set`, later on this same document. However, the following list of helpful reference sources can be visited to gain a more deep knowledge:

- [@ClrHome Z80 Table of Instructions](https://clrhome.org/table/): A well-organized table that provides a concise summary of all Z80 instructions.
- [Zilog's Official Documentation for the Z80 Processor](https://www.zilog.com/docs/z80/um0080.pdf): Especially useful are the last two sections titled *Z80 CPU Instructions* and *Z80 Instruction Set*.
- [Z80 Heaven](http://z80-heaven.wikidot.com/): A web with a detailed information for each instruction.

## Libraries

The `read` directive allows additional files to be included from a main file. These files can be local or located within the installation’s `lib` directory. In this way, it is possible to create libraries that can be shared across projects.

As an example, the **ABASM** distribution includes a small version of the **CPCRSLIB** library and a complete port of **CPCTELERA**. For more information, you can consult the examples available in the `examples/cpcrslib` and `examples/cpctelera` directories.

## Assembler Directives

An assembler directive is an instruction that does not directly translate into machine code for the CPU but provides information or instructions to the assembler on how to process the source code. These directives control aspects of the assembly process, such as code organization, data definition, memory allocation, and constant definitions. Unlike instructions executed by the CPU, directives only affect the assembler during the assembly of the source code. Common examples include ORG (to set the starting address), EQU (to define constants), and DB (to define data in memory). The complete list of directives supported by ABASM and their meanings are as follows:

### ALIGN

- ALIGN n [,v]

*n* must be a number or numerical expression that is a power of two. This directive adds the necessary bytes so that the memory used up to that point by the program is a multiple of *n*. The optional second parameter sets the value used to fill the required memory (a value between 0 and 255). If this second argument is not specified, the memory is filled with zeros.

For example:

```
main:
    LD A, 0xFF
    ALIGN 8
data:
    DB 0xAA, 0xBB, 0xCC
```

This will produce the following binary code:

```
3E FF 00 00 00 00 00 00 AA BB CC
```

### ASSERT

- ASSERT condition

This directive evaluates whether the provided condition is met. If not, it aborts the assembly process. For example, the following code checks that the next instruction to be assembled does not occupy a memory position higher than the start of video memory (0xC000 on the Amstrad CPC).

```
ASSERT @<0xC000
```

The basic logic operators are:
 - *==* : equal than.
 - *!=* : not equal than.
 - *<*, *>* : minor than.  
 - *<=*, *>=*: major than. 

### DB, DM, DEFB, DEFM 

- DEFB  n [,n ...]
- DEFM  n [,n ...]
- DB    n [,n ...]
- DM    n [,n ...]

Stores the provided list of bytes at the current memory location. *n* can be a number or a numerical expression in the range of 0 to 255 (0x00 to 0xFF).

```
DB 0xFF, 0xFF, 0xFF, 0xFF
```

You can also use a text string as a parameter and combine it with the above format. In this case, the ASCII codes of each letter will be stored as if they were the provided numeric values.

```
DB "Hello World",0x00
```

### DS, DEFS, RMEM

- DEFS  n
- DS    n
- RMEM  n

Reserves *n* bytes of memory. Essentially, the current memory position is incremented by *n* bytes, leaving it free for later use.

### DW, DEFW

- DEFW  n [,n ...]
- DW    n [,n ...]

Stores *words* (two bytes in little-endian format) at the current memory location. *n* can be a number or a numerical expression in the range of 0 to 65535 (0x0000 to 0xFFFF).

```
year:
    DW  2024
```

### EQU

- EQU symbol, value
- symbol EQU value

Sets the value of a symbol, typically used as a constant.

```
EQU MEM_VIDEO, 0xC000

LD  A,0xFF
LD  (MEM_VIDEO),A
```

### IF

- IF condition [ELSEIF condition | ELSE] ENDIF

The IF directive allows certain parts of the code to be included or ignored depending on the value of a logical expression. This expression can contain symbols and numerical values. If the expression is true (non-zero), the assembler will process the lines following the IF directive. If it is false (zero), those lines will be ignored.

A basic IF structure could be:

```
IF expression
    ; Assembled code if the expression is true
ELSE
    ; Assembled code if the expression is false
ENDIF
```

This directive is useful when combined with ABASM's `--define` option, which allows changing what code is assembled depending on the call made to the assembler. However, any symbol or constant referenced in the logical expression must have been declared beforehand.

The basic logic operators are:
 - *=* : while == is preferred, ABASM supports '=' because WinAPE syntax does it too.
 - *==* : equal than.
 - *!=* : not equal than.
 - *<*, *>* : minor than.  
 - *<=*, *>=*: major than. 

### IFNOT

- IFNOT condition [ELSEIF condition | ELSE] ENDIF

The IFNOT directive behaves in the same way that the directive `IF`, but the assembler will process the lines following the IFNOT directive when the logical expression is false (equal to zero). If the logical expression is true (non-zero), those lines will be ignored.

### INCBIN

- INCBIN "binary file"

This directive inserts the contents of the file specified in double quotes. The file path should be relative to the location of the file that includes it.

```
INCBIN "./assets/mysprite.bin"
```

### MACRO

- MACRO symbol [param1, param2, ...] ENDM

This directive allows you to assign a name or symbol to a block of code, which extends until the next occurrence of ENDM. The macro can take a list of parameters, which will be replaced by the corresponding values provided in the  *calls* to the macro. Once defined, a macro can be used throughout the rest of the code just like a regular instruction. Each parameter passed is substituted literally into the code inside the macro when it is encountered as a whole word. For that reason, start and finish each parameter name with the character '_' may be a good practice to avoid matches with text strings or register names.

```
macro get_screenPtr _REG_, _X_, _Y_ 
   ld _REG_, &C000 + 80 * (_Y_ / 8) + 2048 * (_Y_ & 7) + _X_ 
endm

main:
   get_screenPtr hl, 20, 10
``` 

Macro code can contain *calls* to other macros but it's not possible to define a new macro or use the directive **read**. If a macro contains a regular label and the macro is *called* more than once, the assembler will detect a symbol redefinition, which will cause an error. For that reason, If a macro needs to use labels, they must be preceded by the symbol '!' which singnales them as **macro local labels**.

```
macro decnz_a
  or a
  jr z,!leave
  dec a
  !leave
mend
```

WinApe uses the symbol '@' to mark **macro local labels** but that symbol is used by ABASM to represent the current instruction's memory address too. As a result, ABASM departs from WinApe in this point.

If a macro is defined twice, ABASM uses the latest processed definition. However, it is also possible to use the directive `MDELETE symbol` to ensure that a current macro definition is not longer available.

### LIMIT

- LIMIT memory_address

Sets the maximum memory address that the assembled program can reach. The provided value can be either a number or a numerical expression. By default, this value is set to 65,536 (64K).

```
LIMIT &C000   ; no code can be written inside the video memory which starts at &C000
ORG &C000
LD A, &FF     ; this line will cause an error
```

### LET

- LET symbol=value

This directive allows changing the value of a symbol or constant. This symbol or constant must have been initially defined with LET.

```
LET PADDING=0x00
<code>
LET PADDING=0xFF
<more code>
```

### READ

- READ "source code file"

This directive inserts the contents of the file specified in double quotes and assembles it. The file path should be relative to the location of the file that includes it. All symbols defined in the inserted file are global, so they must be unique and not repeated in the main file or any other file included using this method.

```
READ "./lib/keyboard.asm"
```

### REPEAT

- REPEAT numeric expression `code block` REND

Repeats a block of code as many times as the value specified by the numeric expression. REPEAT directive cannot be used in the body of a macro definition.

```
EQU ENTITIES, 10
LET ENTITY_ID = 0
REPEAT ENTITIES
  DB 0x00       ; X pos
  DB 0x00       ; Y pos
  DB ENTITY_ID  ; Entity ID
  LET ENTITY_ID = ENTITY_ID + 1
REND
```

### ORG

- ORG memory_address

Specifies the memory address to be considered as the current address from that point forward for any necessary calculations, such as setting the value of a label. Typically, if this directive is used, it appears as the first instruction of the source code, although it's possible to replace it with the ABASM's command line parameter `--start`.

```
ORG 0x4000
```

There is nothing to prevent the source code from including more than one occurrence of this directive, although it is not recommended, as the resulting binary file will fill with 0s any remaining empty memory between the starting memory position for the program and the highest memory written address. This will increase the final `bin` file size. Therefore, if a program needs to have parts loaded in different memory areas, it is advisable to generate a separate binary file for each area and package them all within the same DSK or CDT, along with a loader programmed in BASIC (for example).

### PRINT

- PRINT expression[, expression ...]

Prints the result of the provided expression(s) to the standard output as soon as it is evaluated during assembly. This can be useful for generating additional information during assembly, such as the total memory consumed by the program.

```
ORG 0x4000
<code>
PRINT @-0x4000
```

### SAVE

- SAVE "filename", numeric expression, numeric expression

This directive allows the generation of additional binary files containing the memory where the assembled code is being written. The memory has a maximum size of 64K, which is the limit of the Amstrad CPC 464. The first expression defines the starting address, while the second specifies the total number of bytes to be written to the file.

```
SAVE "myscreen.bin",&C000,&4000
```

### STOP

- STOP

Stops the assembly process issuing an error.

### WHILE

- WHILE logic expression `code block` WEND

It allows a block of code to be assembled repeatedly as long as the specified condition is met. If the condition never becomes false, this directive can result in an infinite loop. WHILE directive cannot be used in the body of a macro definition.

```
LET OBJECTS = 32
WHILE OBJECTS>0
  db 0
  db 0
  db 0
  LET OBJECTS = OBJECTS-1
WEND
```

## Expressions and Special Characters

When an instruction or directive requires a number as a parameter, you can use a mathematical expression instead. These expressions can reference any symbol defined in the code. If the result of an expression is negative, its two's complement is used as the value. Additionally, some symbols have special meanings, as outlined in the following list:

- **$** represents the current instruction's memory address.
- **@** is interchangeable with the **$** symbol.
- **&** prefix indicates hexadecimal numbers (e.g., &FF).
- **0x** prefix indicates hexadecimal numbers (e.g., 0xFF).
- **%** prefix indicates binary numbers (e.g., %11111111).
- **0b** prefix indicates binary numbers (e.g., 0b11111111).
- **"** double quotes delimit characters or strings (1).
- **'** single quotes are equivalent to double quotes for delimiting strings.
- **MOD** represents the modulo operator.
- **AND** represents de bitwise AND operator: op1 AND op2. The Python operator & can be used too.
- **OR** represents de bitwise OR operator: op1 AND op2. The Python operator | can be used too.
- **XOR** represents de bitwise XOR operator: op1 AND op2. The Python operator ^ can be used too.
- **<<** represents the shift left operator.
- **>>** represents the shift right operator.
  
(1) A single character enclosed in double quotes will be converted to its ASCII value in numerical expressions. Double and single quotes can be used to enclose strings but neither can appear in the string body.

# Libraries included in ABASM

`ABASM` includes two libraries ready to use in MAXAM assembler style. They are a terrific knowledge source for the Amstrad CPC specifics, specially regarding their video memory organization.

## CPCRSLIB

CPCRSlib is a C library that provides routines and functions for handling sprites and tile maps on the Amstrad CPC. The library is designed to be used with the Z88DK compiler or with the SDCC compiler. CPCRSlib also includes keyboard routines for key redefinition and detection, as well as general-purpose routines for changing screen modes and colours.

Additionally, CPCRSLIB features a music and sound effects player developed by WYZ, capable of playing music created with WYZTracker.

* A detailed explanation of each function and routine can be found here:
  [http://www.amstrad.es/programacion/cpcrslib.html](http://www.amstrad.es/programacion/cpcrslib.html)
* The original and latest official release of the library can be downloaded from:
  [http://sourceforge/cpcrslib](http://sourceforge/cpcrslib)

The version shipped with `ABASM` does not include support for tile map scrolling. Additionally, some routines have been renamed for clarity and consistency. Please refer to the examples located in `examples/cpcrslib` to learn more about how to use this library within `ABASM`.

## CPCTELERA

CPCtelera is a multiplatform framework for developing games and multimedia software for the Amstrad CPC. It runs on Linux, macOS, and Windows (via Cygwin), and simplifies the process of developing Amstrad CPC software in either C or assembly language. CPCtelera requires the use of the SDCC compiler and its bundled assembler.

CPCtelera is thoroughly documented, featuring a complete reference manual, and its source code is extensively commented. Full details and documentation can be found at:

* [https://lronaldo.github.io/cpctelera/](https://lronaldo.github.io/cpctelera/)
* [https://lronaldo.github.io/cpctelera/files/readme-txt.html](https://lronaldo.github.io/cpctelera/files/readme-txt.html)

The port included in `ABASM` covers all routines available in CPCtelera version 1.5-dev. The main difference is that the `_asm` suffix has been removed from routine names, as there is no ambiguity between C and assembly in this context. To learn more about how to use this library within `ABASM`, programmers can check the examples located in `examples/cpctelera`.

# The Z80 instruction set

This section provides a short list of all Z80 available instructions. While many resources list instruction timing in cycles or T-states, the Amstrad CPC has its own timing due to the Gate Array pausing the Z80 to access video memory. Therefore, it's more accurate to measure timing on the Amstrad CPC based on the cost of the NOP instruction (1 microsecond). Times can be checked in the following web site too:

- [Z80 Timings on Amstrad CPC - Cheat Sheet](https://www.cpcwiki.eu/imgs/b/b4/Z80_CPC_Timings_cheat_sheet.20230709.pdf)

**Key:**
```
r 	  8-bit register (B,C,D,E,H,L,A)
n     8-bit value (range 0-254)
hh 	  8-bit hexadecimal value (range &00-&FF)
d 	  8-bit numeric offset (-128 to 127)

rr 	  16-bit register (HL,DE,BC)
nn    16-bit value (decimal 0-65535))
HHhh 	16-bit value (hexadecimal &0000-&FFFF)

cc	  condition code (z,nz,c,nc,p,m,po,pe)
cn 	  condition not satisfied
cs 	  condition satisfied

b     bit position number (7-0)
```

**Instruction list:**
```
bytes         opcode        timing    explanation
-------------------------------------------------------------------------------
8F          	ADC   A,A       1 Add with carry register r to accumulator.
88          	ADC   A,B
89          	ADC   A,C
8A          	ADC   A,D
8B          	ADC   A,E
8C          	ADC   A,H
8D          	ADC   A,L
CE hh       	ADC   A,n       2 Add with carry value n to accumulator.
DD 8C       	ADC   A,IXH     2 Add with carry high byte from IX to accumulator.
DD 8D       	ADC   A,IXL     2 Add with carry low byte from IX to accumulator.
FD 8C       	ADC   A,IYH     2 Add with carry high byte from IY to accumulator.
FD 8D       	ADC   A,IYL     2 Add with carry low byte from IY to accumulator.
8E          	ADC   A,(HL)    2 Add with carry location (HL) to acccumulator.
DD 8E hh    	ADC   A,(IX+d)  5 Add with carry location (IX+d) to accumulator.
FD 8E hh    	ADC   A,(IY+d)  5 Add with carry location (IY+d) to accumulator.
ED 4A       	ADC   HL,BC     4 Add with carry register pair rr to HL.
ED 5A       	ADC   HL,DE
ED 6A       	ADC   HL,HL
ED 7A       	ADC   HL,SP

87          	ADD   A,A       1 Add register r to accumulator.
80          	ADD   A,B
81          	ADD   A,C
82          	ADD   A,D
83          	ADD   A,E
84          	ADD   A,H
85          	ADD   A,L
C6 hh       	ADD   A,n       2 Add value n to accumulator.
DD 84       	ADD   A,IXH     2 Add high byte from IX to accumulator.
DD 85       	ADD   A,IXL     2 Add low byte from IX to accumulator.
FD 84       	ADD   A,IYH     2 Add high byte from IY to accumulator.
FD 85       	ADD   A,IYL     2 Add low byte from IY to accumulator.
86          	ADD   A,(HL)    2 Add location (HL) to acccumulator.
DD 86 hh    	ADD   A,(IX+d)  5 Add location (IX+d) to accumulator.
FD 86 hh    	ADD   A,(IY+d)  5 Add location (IY+d) to accumulator.
09          	ADD   HL,BC     3 Add register pair rr to HL.
19          	ADD   HL,DE
29          	ADD   HL,HL
39          	ADD   HL,SP
DD 09       	ADD   IX,BC     4 Add register pair rr to IX.
DD 19       	ADD   IX,DE
DD 29       	ADD   IX,IX
DD 39       	ADD   IX,SP
FD 09       	ADD   IY,BC     4 Add register pair rr to IY.
FD 19       	ADD   IY,DE
FD 29       	ADD   IY,IY
FD 39       	ADD   IY,SP

A7          	AND   A         1 Logical AND of register r to accumulator.
A0          	AND   B
A1          	AND   C
A2          	AND   D
A3          	AND   E
A4          	AND   H
A5          	AND   L
E6 hh       	AND   n         2 Logical AND of value n to accumulator.
DD A4       	AND   IXH       2 Logical AND of IX high byte to accumulator.
DD A5       	AND   IXL       2 Logical AND of IX low byte to accumulator.
FD A4       	AND   IYH       2 Logical AND of IY high byte to accumulator.
FD A5       	AND   IYL       2 Logical AND of IY low byte to accumulator.
A6          	AND   (HL)      2 Logical AND of value at location (HL) to accumulator.
DD A6 hh    	AND   (IX+d)    5 Logical AND of value at location (IX+d) to accumulator.
FD A6 hh    	AND   (IY+d)    5 Logical AND of value at location (IY+d) to accumulator.

CB bF       	BIT   b,A       2 Test bit b of register r.
CB b8       	BIT   b,B         Result is stored in flag Z.
CB b9       	BIT   b,C
CB bA       	BIT   b,D
CB bB       	BIT   b,E
CB bC       	BIT   b,H
CB bD       	BIT   b,L
CB bE       	BIT   b,(HL)    3 Test bit b of location (HL).
DD CB hh bE 	BIT   b,(IX+d)  6 Test bit b of location (IX+d).
FD CB hh bE 	BIT   b,(IY+d)  6 Test bit b of location (IY+d).

CD hh HH    	CALL  HHhh      5 Call subroutine at the given memory address.
CC hh HH    	CALL  z,HHhh  3/5 Call subroutine if flag Z is set (5) else (3).
C4 hh HH    	CALL  nz,HHhh 3/5 Call subroutine if flag Z is clear (5) else (3).
DC hh HH    	CALL  c,HHhh  3/5 Call subroutine if flag C is set (5) else (3).
D4 hh HH    	CALL  nc,HHhh 3/5 Call subroutine if flag C is clear (5) else (3).
F4 hh HH    	CALL  p,HHhh  3/5 Call subroutine if flag S is clear (5) else (3).
FC hh HH    	CALL  m,HHhh  3/5 Call subroutine if flag S is set (5) else (3).
EC hh HH    	CALL  pe,HHhh 3/5 Call subroutine if flag P/V is set (5) else (3).
E4 hh HH    	CALL  po,HHhh 3/5 Call subroutine if flag P/V is clear (5) else (3).

3F          	CCF             1 Complement flag C (carry).

BF          	CP    A         1 Compare register r with accumulator.
B8          	CP    B           flag Z set if A == N else clear.
B9          	CP    C           flag C set if A < N else clear (unsigned numbers).   
BA          	CP    D           flag S <> P/V If A < N else S = P/V (signed numbers).  
BB          	CP    E               
BC          	CP    H               
BD          	CP    L
FE hh       	CP    n         2 Compare value n with accumulator.
DD BC       	CP    IXH       1 Compare IX high byte with accumulator.
DD BD       	CP    IXL       1 Compare IX low byte with accumulator.
FD BC       	CP    IYH       1 Compare IY high byte with accumulator.
FD BD       	CP    IYL       1 Compare IY low byte with accumulator.
BE          	CP    (HL)      2 Compare value at location (HL) with accumulator.
DD BE hh    	CP    (IX+d)    5 Compare value at location (IX+d) with accumulator.
FD BE hh    	CP    (IY+d)    5 Compare value at location (IY+d) with accumulator.

ED A9       	CPD             5 Compare location (HL) and acc., decrement HL and BC.
ED B9       	CPDR          5/6 Perform a CPD and repeat until BC=0 (5), if BC<>0 (6).
ED A1       	CPI             5 Compare location (HL) and acc., incr HL, decr BC.
ED B1       	CPIR          5/6 Perform a CPI and repeat until BC=0 (5), if BC<>0 (6).
2F          	CPL             1 Complement accumulator (1's complement).

27          	DAA             1 Decimal adjust accumulator.    

3D          	DEC   A         1 Decrement register r.
05          	DEC   B
0D          	DEC   C
15          	DEC   D
1D          	DEC   E
25          	DEC   H
2D          	DEC   L
DD 25       	DEC   IXH       2 Decrement IX high byte.
DD 2D       	DEC   IXL       2 Decrement IX low byte.
FD 25       	DEC   IYH       2 Decrement IY high byte.
FD 2D       	DEC   IYL       2 Decrement IY low byte.
35          	DEC   (HL)      3 Decrement value at location (HL).
DD 35 hh    	DEC   (IX+d)    6 Decrement value at location (IX+d).
FD 35 hh    	DEC   (IY+d)    6 Decrement value at location (IY+d).
0B          	DEC   BC        2 Decrement register pair rr.
1B          	DEC   DE
2B          	DEC   HL
3B          	DEC   SP
DD 2B       	DEC   IX        3 Decrement IX.
FD 2B       	DEC   IY        3 Decrement IY.

F3          	DI              1 Disable interrupts. (except NMI at 0066h)
hh F4       	DJNZ  n       3/4 Decrement B and jump offset n if B<>0 (4) else (3).
FB          	EI              1 Enable interrupts.

08          	EX    AF,AF'    1 Exchange the contents of AF and AF'.
EB          	EX    DE,HL     1 Exchange the contents of DE and HL.
E3          	EX    (SP),HL   6 Exchange the location (SP) and HL.
DD E3       	EX    (SP),IX   7 Exchange the location (SP) and IX.
FD E3       	EX    (SP),IY   7 Exchange the location (SP) and IY.

D9          	EXX             1 Exchange the contents of BC,DE,HL with BC',DE',HL'.

76          	HALT          1/* Halt computer and wait for interrupt (variable timing).

ED 46       	IM    0         2 Set interrupt mode 0 (instruction on data bus by int device).
ED 56       	IM    1         2 Set interrupt mode 1 (rst 38).
ED 5E       	IM    2         2 Set interrupt mode 2 (vector jump).

DB hh       	IN    A,(n)     3 Load the accumulator with input from device/port n.
ED 40       	IN    B,(C)     4 Load the register r with input from device/port stored in B(!!)[1].
ED 48       	IN    C,(C)
ED 50       	IN    D,(C)
ED 58       	IN    E,(C)
ED 60       	IN    H,(C)
ED 68       	IN    L,(C)

3C          	INC   A         1 Increment register r.
04          	INC   B
0C          	INC   C
14          	INC   D
1C          	INC   E
24          	INC   H
2C          	INC   L
DD 24       	INC   IXH       2 Increment IX high byte.
DD 2C       	INC   IXL       2 Increment IX low byte.
FD 24       	INC   IYH       2 Increment IY high byte.
FD 2C       	INC   IYL       2 Increment IY low byte.
34          	INC   (HL)      3 Increment location (HL).
DD 34 hh    	INC   (IX+d)    6 Increment location (IX+d).
FD 34 hh    	INC   (IY+d)    6 Increment location (IY+d).
03          	INC   BC        2 Increment register pair rr.
13          	INC   DE
23          	INC   HL
33          	INC   SP
DD 23       	INC   IX        3 Increment IX.
FD 23       	INC   IY        3 Increment IY.

ED AA       	IND             5 (HL)=Input from port (C), Decrement HL and B.
ED BA       	INDR          5/6 Perform an IND and repeat until B=0 (5), if B<>0 (6).
ED A2       	INI             5 (HL)=Input from port (C), HL=HL+1, B=B-1.
ED B2       	INIR          5/6 Perform an INI and repeat until B=0 (5), if B<>0 (6).

C3 hh HH    	JP    HHhh      3 Unconditional jump to memory address HHhh.
E9          	JP    (HL)      1 Unconditional jump to address in HL.
DD E9       	JP    (IX)      2 Unconditional jump to address in IX.
FD E9       	JP    (IY)      2 Unconditional jump to address in IY.
CA hh HH    	JP    z,HHhh    3 Jump to address if flag Z is set.
C2 hh HH    	JP    nz,HHhh   3 Jump to address if flag Z is clear.
DA hh HH    	JP    c,HHhh    3 Jump to address if flag C is set.
D2 hh HH    	JP    nc,HHhh   3 Jump to address if flag C is clear.
F2 hh HH    	JP    p,HHhh    3 Jump to address if flag S is clear.
FA hh HH    	JP    m,HHhh    3 Jump to address if flag S is set.
EA hh HH    	JP    pe,HHhh   3 Jump to address if flag P/V is set.
E2 hh HH    	JP    po,HHhh   3 Jump to address if flag P/V is clear.

18 hh       	JR    n         3 Unconditional jump relative to PC+n.       
28 hh       	JR    z,n     2/3 Jump relative to PC+n if flag Z set (3) else (2).
20 hh       	JR    nz,n    2/3 Jump relative to PC+n if flag Z clear (3) else (2).
38 hh       	JR    c,n     2/3 Jump relative to PC+n if flag C set (3) else (2).
30 hh       	JR    nc,n    2/3 Jump relative to PC+n if flag C clear (3) else (2).

7F          	LD    A,A       1 Load accumulator with value stored in register r.
78          	LD    A,B
79          	LD    A,C
7A          	LD    A,D
7B          	LD    A,E
7C          	LD    A,H
7D          	LD    A,L
ED 5F       	LD    A,R       3 Load accumulator with R (memory refresh register).
ED 57       	LD    A,I       3 Load accumulator with I (interrupt vector register).
DD 7C       	LD    A,IXH     2 Load accumulator with the high byte from IX.
DD 7D       	LD    A,IXL     2 Load accumulator with the low byte from IX.
FD 7C       	LD    A,IYH     2 Load accumulator with the high byte from IY.
FD 7D       	LD    A,IYL     2 Load accumulator with the low byte from IY.

47          	LD    B,A       1 Load B with value stored in register r.
40          	LD    B,B
41          	LD    B,C
42          	LD    B,D
43          	LD    B,E
44          	LD    B,H
45          	LD    B,L
DD 44       	LD    B,IXH     2 Load B with the high byte from IX.
DD 45       	LD    B,IXL     2 Load B with the low byte from IX.
FD 44       	LD    B,IYH     2 Load B with the high byte from IY.
FD 45       	LD    B,IYL     2 Load B with the low byte from IY.

4F          	LD    C,A       1 Load C with value stored in register r.
48          	LD    C,B
49          	LD    C,C
4A          	LD    C,D
4B          	LD    C,E
4C          	LD    C,H
4D          	LD    C,L
DD 4C       	LD    C,IXH     2 Load C with the high byte from IX.
DD 4D       	LD    C,IXL     2 Load C with the low byte from IX.
FD 4C       	LD    C,IYH     2 Load C with the high byte from IY.
FD 4D       	LD    C,IYL     2 Load C with the low byte from IY.

57          	LD    D,A       1 Load D with value stored in register r.
50          	LD    D,B
51          	LD    D,C
52          	LD    D,D
53          	LD    D,E
54          	LD    D,H
55          	LD    D,L
DD 54       	LD    D,IXH     2 Load D with the high byte from IX.
DD 55       	LD    D,IXL     2 Load D with the low byte from IX.
FD 54       	LD    D,IYH     2 Load D with the high byte from IY.
FD 55       	LD    D,IYL     2 Load D with the low byte from IY.

5F          	LD    E,A       1 Load E with value stored in register r.
58          	LD    E,B
59          	LD    E,C
5A          	LD    E,D
5B          	LD    E,E
5C          	LD    E,H
5D          	LD    E,L
DD 5C       	LD    E,IXH     2 Load D with the high byte from IX.
DD 5D       	LD    E,IXL     2 Load D with the low byte from IX.
FD 5C       	LD    E,IYH     2 Load D with the high byte from IY.
FD 5D       	LD    E,IYL     2 Load D with the low byte from IY.

67          	LD    H,A       1 Load H with value stored in register r.
60          	LD    H,B
61          	LD    H,C
62          	LD    H,D
63          	LD    H,E
64          	LD    H,H
65          	LD    H,L

6F          	LD    L,A       1 Load L with value stored in register r.
68          	LD    L,B
69          	LD    L,C
6A          	LD    L,D
6B          	LD    L,E
6C          	LD    L,H
6D          	LD    L,L

ED 47       	LD    I,A       3 Load I with accumulator.
ED 4F       	LD    R,A       3 Load R with accumulator.

3E hh       	LD    A,n       2 Load register r with value n.
06 hh       	LD    B,n
0E hh       	LD    C,n
16 hh       	LD    D,n
1E hh       	LD    E,n
26 hh       	LD    H,n
2E hh       	LD    L,n

7E          	LD    A,(HL)    2 Load register r with value at memory address in HL.
46          	LD    B,(HL)
4E          	LD    C,(HL)
56          	LD    D,(HL)
66          	LD    H,(HL)
6E          	LD    L,(HL)

DD 7E hh    	LD    A,(IX+d)  5 Load register r with value at memory address IX+d.
DD 46 hh    	LD    B,(IX+d)
DD 4E hh    	LD    C,(IX+d)
DD 56 hh    	LD    D,(IX+d)
DD 5E hh    	LD    E,(IX+d)
DD 66 hh    	LD    H,(IX+d)
DD 6E hh    	LD    L,(IX+d)
FD 7E hh    	LD    A,(IY+d)  5 Load register r with value at memory address IY+d.
FD 46 hh    	LD    B,(IY+d)
FD 4E hh    	LD    C,(IY+d)
FD 56 hh    	LD    D,(IY+d)
FD 5E hh    	LD    E,(IY+d)
FD 66 hh    	LD    H,(IY+d)
FD 6E hh    	LD    L,(IY+d)

0A          	LD    A,(BC)    2 Load accumulator with value at location (BC).
1A          	LD    A,(DE)    2 Load accumulator with value at location (DE).
3A hh HH    	LD    A,(HHhh)  4 Load accumulator with value at memory address HHhh.

F9          	LD    SP,HL     2 Load SP with HL.
DD F9       	LD    SP,IX     3 Load SP with IX.
FD F9       	LD    SP,IY     3 Load SP with IY.
31 hh HH    	LD    SP,nn     3 Load register pair SP with nn.
ED 7B hh HH 	LD    SP,(HHhh) 6 Load register pair SP with value at memory address nn.

01 hh HH    	LD    BC,nn     3 Load register pair rr with nn.
11 hh HH    	LD    DE,nn
21 hh HH    	LD    HL,nn
DD 21 hh HH 	LD    IX,nn     4 Load IX with value nn.
FD 21 hh HH 	LD    IY,nn     4 Load IY with value nn.

ED 4B hh HH 	LD    BC,(HHhh) 6 Load register pair rr with value at memory address nn.
ED 5B hh HH 	LD    DE,(HHhh)
2A hh HH    	LD    HL,(HHhh)
DD 2A hh HH 	LD    IX,(HHhh) 6 Load IX with value at memory address nn.
FD 2A hh HH 	LD    IY,(HHhh) 6 Load IY with value at memory address nn.

02          	LD    (BC),A    2 Load into memory address stored in rr value in r.
12          	LD    (DE),A
77          	LD    (HL),A
70          	LD    (HL),B
71          	LD    (HL),C
72          	LD    (HL),D
73          	LD    (HL),E
74          	LD    (HL),H
75          	LD    (HL),L
36 hh       	LD    (HL),n    3 Load into memory address HL value n.
DD 36 dd nn 	LD    (IX+d),n  6 Load into memory address IX+d value n.
DD 77 hh    	LD    (IX+d),A  5 Load into memory address IX+d value in register r.
DD 70 hh    	LD    (IX+d),B
DD 71 hh    	LD    (IX+d),C
DD 72 hh    	LD    (IX+d),D
DD 73 hh    	LD    (IX+d),E
DD 74 hh    	LD    (IX+d),H
DD 75 hh    	LD    (IX+d),L
FD 36 dd nn 	LD    (IY+d),n  6 Load into memory address IY+d value n.
FD 77 hh    	LD    (IY+d),A  5 Load into memory address IY+d value in register r.
FD 70 hh    	LD    (IY+d),B
FD 71 hh    	LD    (IY+d),C
FD 72 hh    	LD    (IY+d),D
FD 73 hh    	LD    (IY+d),E
FD 74 hh    	LD    (IY+d),H
FD 75 hh    	LD    (IY+d),L

32 hh HH    	LD    (HHhh),A  4 Load into memory address HHhh value in accumulator.
22 hh HH    	LD    (HHhh),HL 5 Load into memory address HHhh value in HL.
ED 43 hh HH 	LD    (HHhh),BC 6 Load into memory address HHhh value in registr pair rr.
ED 53 hh HH 	LD    (HHhh),DE
DD 22 hh HH 	LD    (HHhh),IX
FD 22 hh HH 	LD    (HHhh),IY
ED 73 hh HH 	LD    (HHhh),SP

ED A8       	LDD             5 Load location (DE) with location (HL), decrement DE,HL,BC.
ED B8       	LDDR          5/6 Perform an LDD and repeat until BC=0 (5) else (6).
ED A0       	LDI             5 Load location (DE) with location (HL), incr DE,HL; decr BC.
ED B0       	LDIR          5/6 Perform an LDI and repeat until BC=0 (5) else (6).

ED 44       	NEG             2 Negate accumulator (2's complement).
00          	NOP             1 No operation.

B7          	OR    A         1 Logical OR of register r and accumulator.
B0          	OR    B
B1          	OR    C
B2          	OR    D
B3          	OR    E
B4          	OR    H
B5          	OR    L
DD B4       	OR    IXH       2 Logical OR of IX high byte and accumulator.
DD B5       	OR    IXL       2 Logical OR of IX low byte and accumulator.
FD B4       	OR    IYH       2 Logical OR of IY high byte and accumulator.
FD B5       	OR    IYL       2 Logical OR of IY low byte and accumulator.
F6 hh       	OR    n         2 Logical OR of value n and accumulator.
B6          	OR    (HL)      2 Logical OR of value at location (HL) and accumulator.
DD B6 hh    	OR    (IX+d)    5 Logical OR of value at location (IX+d) and accumulator.
FD B6 hh    	OR    (IY+d)    5 Logical OR of value at location (IY+d) and accumulator.

ED BB       	OTDR          5/6 Perform an OUTD and repeat until B=0 (5) else (6)[1].
ED B3       	OTIR          5/6 Perform an OTI and repeat until B=0 (5) else (6)[1].
ED 79       	OUT   (C),A     4 Load output port stored in reg B(!!) with value from r[1].
ED 49       	OUT   (C),C
ED 51       	OUT   (C),D
ED 59       	OUT   (C),E
ED 61       	OUT   (C),H
ED 69       	OUT   (C),L
D3 hh       	OUT   (n),A     3 Load output port (n) with accumulator[1].
ED AB       	OUTD            5 Load output port in reg B(!!) with (HL), decrement HL and B[1].
ED A3       	OUTI            5 Load output port in reg B(!!) with (HL), incr HL, decr B[1].

F1          	POP   AF        3 Load register pair rr with top of stack.
C1          	POP   BC
D1          	POP   DE
E1          	POP   HL
DD E1       	POP   IX        5 Load IX with top of stack.
FD E1       	POP   IY        5 Load IY with top of stack.

F5          	PUSH  AF        4 Load register pair rr onto stack.
C5          	PUSH  BC
D5          	PUSH  DE
E5          	PUSH  HL
DD E5       	PUSH  IX        5 Load IX onto stack.
FD E5       	PUSH  IY        5 Load IY onto stack.

CB **       	RES   b,A       2 Reset bit b of register r.
CB **       	RES   b,B         ** The last byte codifies the bit and the
CB **       	RES   b,C            register. The sequence starts in 80 and
CB **       	RES   b,D            ends in BF, the byte is composed as:
CB **       	RES   b,E            1 0 b b b r r r
CB **       	RES   b,H            b = [0-7]
CB **       	RES   b,L            r = B=0, C, D, E, H, L, A=7
CB **       	RES   b,(HL)    4 Reset bit b in value at memory address stored in HL.
DD CB hh ** 	RES   b,(IX+d)  7 Reset bit b in value at location stored in IX+d.
FD CB hh ** 	RES   b,(IY+d)  7 Reset bit b in value at location stored in IY+d.

C9          	RET             3 Return from subroutine.
C8          	RET   z       2/4 Return from subroutine if flag Z is set (4) else (2).
C0          	RET   nz      2/4 Return from subroutine if flag Z is clear (4) else (2).
D8          	RET   c       2/4 Return from subroutine if flag C is set (4) else (2).
D0          	RET   nc      2/4 Return from subroutine if flag C is clear (4) else (2).
F0          	RET   p       2/4 Return from subroutine if flag S is clear (4) else (2).
F8          	RET   m       2/4 Return from subroutine if flag S is set (4) else (2).
E8          	RET   pe      2/4 Return from subroutine if flag P/V is set (4) else (2).
E0          	RET   po      2/4 Return from subroutine if flag P/V is clear (4) else (2).

ED 4D       	RETI            4 Return from interrupt.
ED 45       	RETN            4 Return from non-maskable interrupt.

CB 17       	RL    A         2 Rotate left through register r using flag C:
CB 10       	RL    B           bit 7 is moved into de flag C and current flag
CB 11       	RL    C           value is copied to bit 0.
CB 12       	RL    D
CB 13       	RL    E
CB 14       	RL    H
CB 15       	RL    L
CB 16       	RL    (HL)      4 Rotate left value at memory address in HL. Uses flag C.
DD CB hh 16 	RL    (IX+d)    7 Rotate left value at memory address in IX+d. Uses flag C.
FD CB hh 16 	RL    (IY+d)    7 Rotate left value at memory address in IY+d. Uses flag C.

17          	RLA             1 Rotate left accumulator through carry. Uses flag C.

CB 07       	RLC   A         2 Rotate register r left circular.
CB 00       	RLC   B
CB 01       	RLC   C
CB 02       	RLC   D
CB 03       	RLC   E
CB 04       	RLC   H
CB 05       	RLC   L
CB 06       	RLC   (HL)      4 Rotate value in memory address HL left circular.
DD CB hh 06 	RLC   (IX+d)    7 Rotate value in memory address IX+d left circular.
FD CB hh 06 	RLC   (IY+d)    7 Rotate value in memory address IY+d left circular.

07          	RLCA            1 Rotate left circular accumulator.
ED 6F       	RLD             5 Rotate nibbles left and right between A and (HL):
                                A low nibble -> (HL) low nibble -> (HL) high nibble ->
                                A low nibble.

CB 1F       	RR    A         2 Rotate right through carry register r using flag C:
CB 18       	RR    B           bit 0 is moved into de flag C and current flag
CB 19       	RR    C           value is copied to bit 7.
CB 1A       	RR    D
CB 1B       	RR    E
CB 1C       	RR    H
CB 1D       	RR    L
CB 1E       	RR    (HL)      4 Rotate right through carry value at location HL.
DD CB hh 1E 	RR    (IX+d)    7 Rotate right through carry value at location IX+d.
FD CB hh 1E 	RR    (IY+d)    7 Rotate right through carry value at location IY+d.

1F          	RRA             1 Rotate right accumulator through carry.

CB 0F       	RRC   A         2 Rotate register r right circular.
CB 08       	RRC   B
CB 09       	RRC   C
CB 0A       	RRC   D
CB 0B       	RRC   E
CB 0C       	RRC   H
CB 0D       	RRC   L
CB 0E       	RRC   (HL)      4 Rotate value at location HL right circular.
DD CB hh 0E 	RRC   (IX+d)    7 Rotate value at location IX+d right circular.
FD CB hh 0E 	RRC   (IY+d)    7 Rotate value at location HL+d right circular.

0F          	RRCA            1 Rotate right circular accumulator.
ED 67       	RRD             5 Rotate nibbles roght and left between A and (HL):
                                A low nibble -> (HL) high nibble -> (HL) low nibble ->
                                A low nibble.

C7          	RST   &00       4 RESET. Reserved [2]. Resets the system.
CF          	RST   &08       4 LOW JUMP. Reserved [2]. Jumps to a routine in the lower 16K.
D7          	RST   &10       4 SIDE CALL. Reserved [2]. Calls a routine in an associated ROM.
DF          	RST   &18       4 FAR CALL. Reserved [2]. Calls a routine anywhere in memory.
E7          	RST   &20       4 RAM LAM. Reserved [2]. Reads the byte from RAM at the address of HL.
EF          	RST   &28       4 FIRM JUMP. Reserved [2]. Jumps to a routine in the lower ROM.
F7          	RST   &30       4 USER RST. Avaiable for the user to extend the instruction set.
FF          	RST   &38       4 INTERRUPT. Reserver [2]. Reserverd for interrupts.

9F          	SBC   A,A       1 Subtract register r from accumulator with carry.
98          	SBC   A,B
99          	SBC   A,C
9A          	SBC   A,D
9B          	SBC   A,E
9C          	SBC   A,H
9D          	SBC   A,L
DD 9C       	SBC   A,IXH     2 Subtract IX high byte from accumulator with carry.
DD 9D       	SBC   A,IXL     2 Subtract IX low byte from accumulator with carry.
FD 9C       	SBC   A,IYH     2 Subtract IY high byte from accumulator with carry.
FD 9D       	SBC   A,IYL     2 Subtract IY low byte from accumulator with carry.
DE hh       	SBC   A,n       2 Subtract value n from accumulator with carry.
9E          	SBC   A,(HL)    2 Subtract value at location in HL from A with carry.
DD 9E hh    	SBC   A,(IX+d)  5 Subtract value at location in IX+d from A with carry.
FD 9E hh    	SBC   A,(IY+d)  5 Subtract value at location in IX+d from A with carry.
ED 42       	SBC   HL,BC     4 Subtract register pair rr from HL with carry.
ED 52       	SBC   HL,DE
ED 62       	SBC   HL,HL
ED 72       	SBC   HL,SP

37          	SCF             1 Set carry flag (C=1).

CB **       	SET   b,A       2 Set bit b of register r.
CB **       	SET   b,B         ** The last byte codifies the bit and the
CB **       	SET   b,C            register. The sequence starts in 80 and
CB **       	SET   b,D            ends in BF, the byte is composed as:
CB **       	SET   b,E            1 1 b b b r r r
CB **       	SET   b,H            b = [0-7]
CB **       	SET   b,L            r = B=0, C, D, E, H, L, A=7
CB **       	SET   b,(HL)    4 Set bit b of value at memory address in HL.
DD CB hh ** 	SET   b,(IX+d)  7 Set bit b of value at memory address in IX+d.
FD CB hh ** 	SET   b,(IY+d)  7 Set bit b of value at memory address in IY+d.          

CB 27       	SLA   A         2 Shift register r left arithmetic.
CB 20       	SLA   B           Bit 7 is moved into flag C.
CB 21       	SLA   C           Bit 0 is set to 0.
CB 22       	SLA   D
CB 23       	SLA   E
CB 24       	SLA   H
CB 25       	SLA   L
CB 26       	SLA   (HL)      4 Shift value at location in HL left arithmetic.
DD CB hh 26 	SLA   (IX+d)    7 Shift value at location in IX+d left arithmetic.
FD CB hh 26 	SLA   (IY+d)    7 Shift value at location in IY+d left arithmetic.

CB 37       	SLL   A         2 Shift register r left "logical".
CB 30       	SLL   B           Bit 7 is moved into flag C.
CB 31       	SLL   C           Bit 0 is set to 1.
CB 32       	SLL   D
CB 33       	SLL   E
CB 34       	SLL   H
CB 35       	SLL   L
CB 36       	SLL   (HL)      4 Shift value at location in HL left logical.
DD CB hh 36 	SLL   (IX+d)    7 Shift value at location in IX+d left logical.
FD CB hh 36 	SLL   (IY+d)    7 Shift value at location in IY+d left logical.

CB 2F       	SRA   A         2 Shift register r right "arithmetically".
CB 28       	SRA   B           Bit 0 is copied into the flag C.
CB 29       	SRA   C           Bit 7 is set to 0.
CB 2A       	SRA   D
CB 2B       	SRA   E
CB 2C       	SRA   H
CB 2D       	SRA   L
CB 2E       	SRA   (HL)      4 Shift value at location in HL right. Bit 7 = 0.
DD CB hh 2E 	SRA   (IX+d)    7 Shift value at location in IX+d right. Bit 7 = 0.
FD CB hh 2E 	SRA   (IY+d)    7 Shift value at location in IY+d right. Bit 7 = 0.

CB 3F       	SRL   A         2 Shift register r right "logically".
CB 38       	SRL   B           Bit 0 is copied into the flag C.
CB 39       	SRL   C           Bit 7 is set to 1.
CB 3A       	SRL   D
CB 3B       	SRL   E
CB 3C       	SRL   H
CB 3D       	SRL   L
CB 3E       	SRL   (HL)      4 Shift value at location in HL right. Bit 7 = 1.
DD CB hh 3E 	SRL   (IX+d)    7 Shift value at location in IX+d right.  Bit 7 = 1.
FD CB hh 3E 	SRL   (IY+d)    7 Shift value at location in IY+d right.  Bit 7 = 1.

97          	SUB   A         1 Subtract register r from accumulator.
90          	SUB   B
91          	SUB   C
92          	SUB   D
93          	SUB   E
94          	SUB   H
95          	SUB   L
D6 hh       	SUB   n         2 Subtract value n from accumulator.
DD 94       	SUB   IXH       2 Subtract IX high byte from accumulator.
DD 95       	SUB   IXL       2 Subtract IX low byte from accumulator.
FD 94       	SUB   IYH       2 Subtract IY high byte from accumulator.
FD 95       	SUB   IYL       2 Subtract IY low byte from accumulator.
96          	SUB   (HL)      2 Subtract value at location in HL from accumulator.
DD 96 hh    	SUB   (IX+d)    5 Subtract value at location in IX+d from accumulator.
FD 96 hh    	SUB   (IY+d)    5 Subtract value at location in IY+d from accumulator.

AF          	XOR   A         1 Exclusive OR register r and accumulator.
A8          	XOR   B
A9          	XOR   C
AA          	XOR   D
AB          	XOR   E
AC          	XOR   H
AD          	XOR   L
EE hh       	XOR   n         2 Exclusive OR value n and accumulator.
DD AC       	XOR   IXH       2 Exclusive OR IX high byte and accumulator.
DD AD       	XOR   IXL       2 Exclusive OR IX low byte and accumulator.
FD AC       	XOR   IYH       2 Exclusive OR IY high byte and accumulator.
FD AD       	XOR   IYL       2 Exclusive OR IY low byte and accumulator.
AE          	XOR   (HL)      2 Exclusive OR value at location in HL and accumulator.
DD AE hh    	XOR   (IX+d)    5 Exclusive OR value at location in IX+d and accumulator.
FD AE hh    	XOR   (IY+d)    5 Exclusive OR value at location in IY+d and accumulator.

```

**[1]** It's important to remember that OUT/IN family instructions use `BC` content and not only C, even if the op code is `OUT (C)`. In Amstrad CPC, instructions OUTD, OUTI, OTIR, etc., don't make much sense because AMSTRAD CPC uses register `B`(!!) from the address in BC to store the port number and not `C` as many other Z80 machines do. 

**[2]** All the Z80 restart instructions, except for one, have been reserved for system use. RST 1 to RST 5 (&08-&28) are used to extend the instruction set by implementing special call and jump instructions that enable and disable ROMs. RST 6 (&30) is available to the user. More information can be obtained here: [ROMs. RAM and Restart Instructions.](https://www.cpcwiki.eu/imgs/f/f6/S968se02.pdf)

# Changelog

- Version 1.4.4
  * Some minor fixes and improvements.
  
- Version 1.4.3
  * Fixed some error messages in DSK tool.
  * Fixed an error encoding raw blocks in CDT tool.
  * Some other minor fixes and improvements.

- Version 1.4.2
  * Remove line endings from source code as it can affect error messages.
  * DSK tool can now set system and read-only flags.

- Version 1.4.1 - 09/02/2026
  * Some fixes in cpctelera assembly code.
  * Better error messages in CDT/DSK tools.
  * IMG tool supports now multiple input files.

- Version 1.4.0 - 07/01/2026
  * New directive IFNOT
  * New tool `IMG`

- Version 1.3.1 - 28/12/2025
  * CPCTELERA examples were not working from the DSK.
  * Fix EOL in ASCII files added to DSK or CDT files.
  * Make.sh scripts added in all examples (Linux and macOS).
 
- Version 1.3.0 - 27/12/2025
  * New directive MDELETE to delete an already defined macro.
  * Macros without arguments were not working as expected.
  * Abasm shows the correct error messages if REPEAT or WHILE directives are used inside a macro body.
  * Port of CPCTELERA library.
  * New tool `asmprj` that allows users to create of basic project structure.

- Version 1.2.0 - 15/12/2025
  * Support for libraries, asm files placed inside the `lib` directory.
  * Port of a section of CPCRSLIB as an example of a library in ABASM.
  * new flag `-s` `--sfile` that generated a new .s file with all assembled code in one file, including the code imported from other files.
  * Better handle of multiple ORG occurrences.
  * Only import once a given ASM file if it's referenced by multiple READ directives.
  * Some other minor fixes and improvements.

- Version 1.1.3 - 16/04/2025
  * Utility bindiff added to the set.
  * ELSEIF directive fixed.
  * New option `--tolerance` controls if warnings must be managed as errors or be completely ignored.
  * Some other minor fixes and improvements.

- Version 1.1.2 - 26/03/2025
  * Z80 instruction list has been updated to include the machine code per instruction.
  * DB directive using math expressions including characters was not working.
  * Some other minor fixes and improvements.

- Version 1.1.1 - 09/03/2025
  * SLL opcodes were not recognized.
  * EX AF,AF' has been fixed.
  * Z80 Instruction Set section added to the manuals.
  * Some other minor fixes and improvements.

- Version 1.1.0 - 06/03/2025
  * Support for directive LIMIT.
  * Support for local labels in macro code.
  * New assembler flag --verbose added as an option.
  * Adding Tests that can be run with python -m unittest
  * Some minor fixes and improvements.

- Version 1.0.0 - 03/10/2024
  * First released version.



