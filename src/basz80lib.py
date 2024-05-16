"""
Library of fragments of code that implements the stack machine intermediate
code in Z80 assembler.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation in its version 3.

This program is distributed in the hope that it will be useful
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
"""

#
# Stack machine to Z80 code fragments 
#
SM2Z80 = {
    'NOP': [],
    'LABEL':  ["$ARG1:"],
    'REM':    ["; $ARG1"], 
    'PUSH':   ["push    hl"],
    'CLEAR':  ["ld      hl,0"],
    'DROP':   ["pop     de"],
    'LDVAL':  ["ld      hl,$ARG1"],
    'LDADDR': ["ld      hl,$ARG1"],
    'LDLREF': [
        "ld      hl,$ARG1",
        "push    ix",
        "pop     de",
        "add     hl,de"
        ],
    'LDGLOB': ["ld      hl,($ARG1)"],
    'LDLOCL': [
        "ld      h,(ix+H)",
        "ld      l,(ix+L)"
        ],
    'STGLOB': ["ld      ($ARG1),hl"],
    'STLOCL': [
        "ld      (ix+H),h",
        "ld      (ix+L),l"
        ],
    'STINDR': [
        "ex de,hl",
        "pop hl",
        "ld (hl),e",
        "inc hl",
        "ld (hl),d"
        ],
    'STINDB': [
        "ex de,hl",
        "pop hl",
        "ld (hl),e"
        ],
    'INCGLOB': [
        "ld hl,$ARG1",
        "inc (hl)",
        "jrnz +2",
        "inc hl",
        "inc (hl)"
        ],
    'INCLOCL': [
        "inc (ix+L)",
        "jrnz +3",
        "inc (ix+H)"
        ],
    'INCR': [
        "ld de,$ARG1",
        "add hl,de"
        ],
    'STACK': [
        "ld hl,$ARG1",
        "add hl,sp",
        "ld sp,hl"
        ],
    'UNSTACK': [
        "ex de,hl",
        "ld hl,$ARG1",
        "add hl,sp",
        "ld sp,hl",
        "ex de,hl"
        ],
    'LOCLVEC': ["push hl"],
    'GLOBVEC': ["ld ($ARG1),hl"],
    'INDEX': [
        "add hl,hl",
        "pop de",
        "add hl,de"
        ],
    'DEREF': [
        "ld a,(hl)",
        "inc hl",
        "ld h,(hl)",
        "ld l,a"
        ],
    'INDXB': [
        "pop de",
        "add hl,de"
        ],
    'DREFB': [
        "ld l,(hl)",
        "ld h,0"
        ],
    'CALL': ["call $ARG1"],
    'CALR': ["call &014A"],  # AAA Revisar
    'JUMP': ["jp $ARG1"],
    'RJUMP': ["jr $ARG1"],  # being $ARG1 = $L in original code
    'JMPFALSE': [
        "ld a,h",
        "or l",
        "jpz $ARG1"
        ],
    'JMPTRUE': [
        "ld a,h",
        "or l",
        "jpnz $ARG1"
        ],
    'FOR': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "jpp $ARG1"
        ],
    'FORDOWN': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpp $ARG1"
        ],
    'MKFRAME': [
        "push ix",
        "ld ix,0",
        "add ix,sp"
        ],
    'DELFRAME': ["pop ix"],
    'RET': ["ret"],
    'HALT': ["jp 0"],
    'NEG': [
        "ld de,0",
        "ex de,hl",
        "xor a",
        "sbc hl,de"
        ],
    'INV': [
        "ld de,&FFFF",
        "ex de,hl",
        "xor a",
        "sbc hl,de"
        ],
    'LOGNOT': [
        "ex de,hl",
        "ld hl,&FFFF",
        "ld a,d",
        "or e",
        "jrnz +1",
        "inc hl"
        ],
    'ADD': [
        "pop de",
        "add hl,de"
        ],
    'SUB': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de"
        ],
    'MUL': [
        "pop de",
        "call &0108"  # AAA Revisar
        ],
    'DIV': [
        "pop de",
        "call &010B"  # AAA Revisar
        ],
    'MOD': [        
        "pop de",
        "call &010E"  # AAA Revisar
        ],
    'AND': [
        "pop de",
        "ld a,h",
        "and d",
        "ld h,a",
        "ld a,l",
        "and e",
        "ld l,a"
        ],
    'OR': [
        "pop de",
        "ld a,h",
        "or d",
        "ld h,a",
        "ld a,l",
        "or e",
        "ld l,a"
        ],
    'XOR': [
        "pop de",
        "ld a,h",
        "xor d",
        "ld h,a",
        "ld a,l",
        "xor e",
        "ld l,a"
        ],
    'SHL': [
        "pop de",
        "ex de,hl",
        "ld b,e",
        "add hl,hl",
        "djnz -3"
        ],
    'SHR': [
        "pop de",
        "ex de,hl",
        "ld b,e",
        "srl h",
        "rr l",
        "djnz -6"
        ],
    'EQ': [
        "pop de",
        "xor a"
        "sbc hl,de",
        "ld hl,&FFFF",
        "jrz +1",
        "inc hl"
        ],
    'NE': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "ld hl,&FFFF",
        "jrnz +1",
        "inc hl"
        ],
    'LT': [
        "pop de",
        "ex de,hl",
        "call &0117", # AAA revisar
        "ld hl,&FFFF",
        "jrc +1",
        "inc hl"
        ],
    'GT': [
        "pop de",
        "call &0117", # AAA revisar
        "ld hl,&FFFF",
        "jrc +1",
        "inc hl"
        ],
    'LE': [
        "pop de",
        "call &0117",
        "ld hl,0",
        "jrc +1",
        "dec hl"
        ],
    'GE': [
        "pop de",
        "ex de,hl",
        "call &0117", # AAA revisar
        "ld hl,0",
        "jrc +1",
        "dec hl"
        ],
    'UMUL': [
        "pop de",
        "call &0111" # AAA revisar
        ],
    'UDIV': [
        "pop de",
        "ex de,hl",
        "call &0114" # AAA revisar
        ],
    'ULT': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "ld hl,&FFFF",
        "jrc +1",
        "inc hl"
        ],
    'UGT': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "ld hl,&FFFF",
        "jrc +1",
        "inc hl"
        ],
    'ULE': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "ld hl,0",
        "jrc +1",
        "dec hl"
        ],
    'UGE': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "ld hl,0",
        "jrc +1",
        "dec hl"
        ],
    'JMPEQ': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpz $ARG1"
        ],
    'JMPNE': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpnz $ARG1"
        ],
    'JMPLT': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "jpm $ARG1"
        ],
    'JMPGT': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpm $ARG1"
        ],
    'JMPLE': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpp $ARG1"
        ],
    'JMPGE': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "jpp $ARG1"
        ],
    'JMPULT': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "jpc $ARG1"
        ],
    'JMPUGT': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpc $ARG1"
        ],
    'JMPULE': [
        "pop de",
        "xor a",
        "sbc hl,de",
        "jpnc $ARG1"
        ],
    'JMPUGE': [
        "pop de",
        "ex de,hl",
        "xor a",
        "sbc hl,de",
        "jpnc $ARG1"
        ],
    'SKIP': ["jp $ARG1"]
}

#
# Amstrad 6128 firmware calls 
#
class FWCALL:
    TXT_INITIALISE      = "&BB4E"
    TXT_RESET           = "&BB51"
    TXT_VDU_ENABLE      = "&BB54"
    TXT_VDU_DISABLE     = "&BB57"
    TXT_OUTPUT          = "&BB5A"
    TXT_WR_CHAR         = "&BB5D"
    TXT_RD_CHAR         = "&BB60"
    TXT_SET_GRAPHIC     = "&BB63"
    TXT_WIN_ENABLE      = "&BB66"
    TXT_GET_WINDOW      = "&BB69"
    TXT_CLEAR_WINDOW    = "&BB6C"
    TXT_SET_COLUMN      = "&BB6F"
    TXT_SET_ROW         = "&BB72"
    TXT_SET_CURSOR      = "&BB75"
    TXT_GET_CURSOR      = "&BB78"
    TXT_CUR_ENABLE      = "&BB7B"
    TXT_CUR_DISABLE     = "&BB7E"
    TXT_CUR_ON          = "&BB81"
    TXT_CUR_OFF         = "&BB84"
    TXT_VALIDATE        = "&BB87"
    TXT_PLACE_CURSOR    = "&BB8A"
    TXT_REMOVE_CURSOR   = "&BB8D"
    TXT_SET_PEN         = "&BB90"
    TXT_GET_PEN         = "&BB93"
    TXT_SET_PAPER       = "&BB96"
    TXT_GET_PAPER       = "&BB99"
    TXT_INVERSE         = "&BB9C"
    TXT_SET_BACK        = "&BB9F"
    TXT_GET_BACK        = "&BBA2"
    TXT_GET_MATRIX      = "&BBA5"
    TXT_SET_MATRIX      = "&BBA8"
    TXT_SET_M_TABLE     = "&BBAB"
    TXT_GET_M_TABLE     = "&BBAE"
    TXT_GET_CONTROLS    = "&BBB1"
    TXT_STR_SELECT      = "&BBB4"
    TXT_SWAP_STREAMS    = "&BBB7"

    SCR_INITIALISE      = "#BBFF"
    SCR_RESET           = "#BC02"
    SCR_SET_OFFSET      = "#BC05"
    SCR_SET_BASE        = "#BC08"
    SCR_GET_LOCATION    = "#BC0B"
    SCR_SET_MODE        = "#BC0E"
    SCR_GET_MODE        = "#BC11"
    SCR_CLEAR           = "#BC14"
    SCR_CHAR_LIMITS     = "#BC17"
    SCR_CHAR_POSITION   = "#BC1A"
    SCR_DOT_POSITION    = "#BC1D"
    SCR_NEXT_BYTE       = "#BC20"
    SCR_PREV_BYTE       = "#BC23"
    SCR_NEXT_LINE       = "#BC26"
    SCR_PREV_LINE       = "#BC29"
    SCR_INK_ENCODE      = "#BC2C"
    SCR_INK_DECODE      = "#BC2F"
    SCR_SET_INK         = "#BC32"
    SCR_GET_INK         = "#BC35"
    SCR_SET_BORDER      = "#BC38"
    SCR_GET_BORDER      = "#BC3B"
    SCR_SET_FLASHING    = "#BC3E"
    SCR_GET_FLASHING    = "#BC41"
    SCR_FILL_BOX        = "#BC44"
    SCR_FLOOD_BOX       = "#BC17"
    SCR_CHAR_INVERT     = "#BC4A"
    SCR_HW_ROLL         = "#BC4D"
    SCR_SW_ROLL         = "#BC50"
    SCR_UNPACK          = "#BC53"
    SCR_REPACK          = "#BC56"
    SCR_ACCESS          = "#BC59"
    SCR_PIXELS          = "#BC5C"
    SCR_HORIZONTAL      = "#BC5F"
    SCR_VERTICAL        = "#BC62"

#
# Utility routines and libraries
#

STRLIB = {
    "strlib_print_nl": [
        "strlib_print_nl:\n",
        "\tld      a, 13\n",
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tld      a, 10\n",
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tret\n\n"
    ],
    "strlib_print_str": [
        "strlib_print_str:\n",
        "\tld      a, (hl)\n",
        "\tcp      0\n",
        "\tret     z\n",
        "\tinc     hl\n",
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tjr      strlib_print_str\n\n"
    ],
}