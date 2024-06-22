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
    'NOP':    [],
    'LABEL':  ["$ARG1:"],
    'REM':    ["; $ARG1"], 
    'PUSH':   ["push    hl"],
    'CLEAR':  ["ld      hl,0"],
    'DROP':   ["pop     de"],
    'LDVAL':  ["ld      hl,$ARG1"],
    'LDMEM':  ["ld      hl,($ARG1)"],
    'STMEM':  ["ld      ($ARG1),hl"],
    'LDLREF': [
        "ld      hl,$ARG1",
        "push    ix",
        "pop     de",
        "add     hl,de"
        ],
    'LDLOCL': [
        "ld      h,(ix+H)",
        "ld      l,(ix+L)"
        ],
    'STLOCL': [
        "ld      (ix+H),h",
        "ld      (ix+L),l"
        ],
    'STINDR': [
        "ex      de,hl",
        "pop     hl",
        "ld      (hl),e",
        "inc     hl",
        "ld      (hl),d"
        ],
    'STINDB': [
        "ex      de,hl",
        "pop     hl",
        "ld      (hl),e"
        ],
    'INCGLOB': [
        "ld      hl,$ARG1",
        "inc     (hl)",
        "jrnz    $+2",
        "inc     hl",
        "inc     (hl)"
        ],
    'INCLOCL': [
        "inc     (ix+L)",
        "jrnz    $+3",
        "inc     (ix+H)"
        ],
    'INC': ["inc     hl"],
    'INCR': [
        "ld      de,$ARG1",
        "add     hl,de"
        ],
    'STACK': [
        "ld      hl,$ARG1",
        "add     hl,sp",
        "ld      sp,hl"
        ],
    'UNSTACK': [
        "ex      de,hl",
        "ld      hl,$ARG1",
        "add     hl,sp",
        "ld      sp,hl",
        "ex      de,hl"
        ],
    'LOCLVEC': ["push    hl"],
    'GLOBVEC': ["ld      ($ARG1),hl"],
    'INDEX': [
        "add     hl,hl",
        "pop     de",
        "add     hl,de"
        ],
    'DEREF': [
        "ld      a,(hl)",
        "inc     hl",
        "ld      h,(hl)",
        "ld      l,a"
        ],
    'INDXB': [
        "pop     de",
        "add     hl,de"
        ],
    'DREFB': [
        "ld      l,(hl)",
        "ld      h,0"
        ],
    'CALL':  ["call    $ARG1"],
    'JUMP':  ["jp      $ARG1"],
    'RJUMP': ["jr      $ARG1"],  # being $ARG1 = $L in original code
    'JMPFALSE': [
        "ld      a,h",
        "or      l",
        "jp      z,$ARG1"
        ],
    'JMPTRUE': [
        "ld      a,h",
        "or      l",
        "jp      nz,$ARG1"
        ],
    'FOR': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      c,$ARG1"
        ],
    'FORDOWN': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "jp      c,$ARG1"
        ],
    'MKFRAME': [
        "push    ix",
        "ld      ix,0",
        "add     ix,sp"
        ],
    'DELFRAME': ["pop     ix"],
    'RET': ["ret"],
    'HALT': ["halt"],
    'NEG': [
        "ld      de,0",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de"
        ],
    'INV': [
        "ld      de,&FFFF",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de"
        ],
    'LOGNOT': [
        "ex      de,hl",
        "ld      hl,&FFFF",
        "ld      a,d",
        "or      e",
        "jrnz    $+3",
        "inc     hl"
        ],
    'ADD': [
        "pop     de",
        "add     hl,de"
        ],
    'SUB': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de"
        ],
    'MUL': [
        "pop     de",
        "call    mul16_signed"
        ],
    'DIV': [
        "pop     de",
        "call    div16_signed"
        ],
    'MOD': [        
        "pop     de",
        "call    mod_16"
        ],
    'AND': [
        "pop     de",
        "ld      a,h",
        "and     d",
        "ld      h,a",
        "ld      a,l",
        "and     e",
        "ld      l,a"
        ],
    'OR': [
        "pop     de",
        "ld      a,h",
        "or      d",
        "ld      h,a",
        "ld      a,l",
        "or      e",
        "ld      l,a"
        ],
    'XOR': [
        "pop     de",
        "ld      a,h",
        "xor     d",
        "ld      h,a",
        "ld      a,l",
        "xor     e",
        "ld      l,a"
        ],
    'SHL': [
        "pop     de",
        "ex      de,hl",
        "ld      b,e",
        "add     hl,hl",
        "djnz    -3"
        ],
    'SHR': [
        "pop     de",
        "ex      de,hl",
        "ld      b,e",
        "srl     h",
        "rr      l",
        "djnz    -6"
        ],
    'EQ': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "ld      hl,&FFFF  ; hl = -1",
        "jr      z,$+3",
        "inc     hl        ; hl = 0"
        ],
    'NE': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "ld      hl,&FFFF  ; hl = -1",
        "jr      nz,$+3",
        "inc     hl        ; hl = 0"
        ],
    'LT': [
        "pop     de",
        "ex      de,hl",
        "call    comp16_signed",
        "ld      hl,&FFFF  ; hl = -1",
        "jr      c,$+3",
        "inc     hl        ; hl = 0"
        ],
    'GT': [
        "pop     de",
        "call    comp16_signed",
        "ld      hl,&FFFF  ; hl = -1",
        "jr      c,$+3",
        "inc     hl        ; hl = 0"
        ],
    'LE': [
        "pop     de",
        "call    comp16_signed",
        "ld      hl,0      ; hl = 0",
        "jr      c,$+3",
        "dec     hl        ; hl = -1"
        ],
    'GE': [
        "pop     de",
        "ex      de,hl",
        "call    comp16_signed",
        "ld      hl,0      ; hl = 0",
        "jr      c,$+3",
        "dec     hl        ; hl = -1"
        ],
    'UMUL': [
        "pop     de",
        "call    mul16_unsigned"
        ],
    'UDIV': [
        "pop     de",
        "ex      de,hl",
        "call    div16_unsigned"
        ],
    'ULT': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "ld      hl,&FFFF  ; hl = -1",
        "jr      c,$+3",
        "inc     hl        ; hl = 0"
        ],
    'UGT': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "ld      hl,&FFFF  ; hl = -1",
        "jr      c,$+3",
        "inc     hl        ; hl = 0"
        ],
    'ULE': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "ld      hl,0      ; hl = 0",
        "jr      c,$+3",
        "dec     hl        ; hl = -1"
        ],
    'UGE': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "ld      hl,0      ; hl = 0",
        "jr      c,$+3",
        "dec     hl        ; hl = -1"
        ],
    'JMPEQ': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      z,$ARG1"
        ],
    'JMPNE': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      nz,$ARG1"
        ],
    'JMPLT': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "jp      m,$ARG1"
        ],
    'JMPGT': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      m,$ARG1"
        ],
    'JMPLE': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      p,$ARG1"
        ],
    'JMPGE': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "jp      p,$ARG1"
        ],
    'JMPULT': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "jp      c,$ARG1"
        ],
    'JMPUGT': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      c,$ARG1"
        ],
    'JMPULE': [
        "pop     de",
        "xor     a",
        "sbc     hl,de",
        "jp      nc,$ARG1"
        ],
    'JMPUGE': [
        "pop     de",
        "ex      de,hl",
        "xor     a",
        "sbc     hl,de",
        "jp      nc,$ARG1"
        ],
    'SKIP': ["jp     $ARG1"]
}

#
# Amstrad 6128 firmware calls 
#
class FWCALL:
    KM_INITIALISE       = "&BB00"
    KM_RESET            = "&BB03"
    KM_WAIT_CHAR        = "&BB06"
    KM_READ_CHAR        = "&BB09"
    KM_CHAR_RETURN      = "&BB0C"
    KM_SET_EXPAND       = "&BB0F"
    KM_GET_EXPAND       = "&BB12"
    KM_EXP_BUFFER       = "&BB15"
    KM_WAIT_KEY         = "&BB18"
    KM_READ_KEY         = "&BB1B"
    KM_TEST_KEY         = "&BB1E"
    KM_GET_STATE        = "&BB21"
    KM_GET_JOYSTICK     = "&BB24"
    KM_SET_TRANSLATE    = "&BB27"
    KM_GET_TRANSLATE    = "&BB2A"
    KM_SET_SHIFT        = "&BB2D"
    KM_GET_SHIFT        = "&BB30"
    KM_SET_CONTROL      = "&BB33"
    KM_GET_CONTROL      = "&BB36"
    KM_SET_REPEAT       = "&BB39"
    KM_GET_REPEAT       = "&BB3C"
    KM_SET_DELAY        = "&BB3F"
    KM_GET_DELAY        = "&BB42"
    KM_ARM_BREAK        = "&BB45"
    KM_DISARM_BREAK     = "&BB48"
    KM_BREAK_EVENT      = "&BB4B"
    KM_TEST_BREAK       = "&BDEE"
    KM_SCAN_KEYS        = "&BDF4"

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

    SCR_INITIALISE      = "&BBFF"
    SCR_RESET           = "&BC02"
    SCR_SET_OFFSET      = "&BC05"
    SCR_SET_BASE        = "&BC08"
    SCR_GET_LOCATION    = "&BC0B"
    SCR_SET_MODE        = "&BC0E"
    SCR_GET_MODE        = "&BC11"
    SCR_CLEAR           = "&BC14"
    SCR_CHAR_LIMITS     = "&BC17"
    SCR_CHAR_POSITION   = "&BC1A"
    SCR_DOT_POSITION    = "&BC1D"
    SCR_NEXT_BYTE       = "&BC20"
    SCR_PREV_BYTE       = "&BC23"
    SCR_NEXT_LINE       = "&BC26"
    SCR_PREV_LINE       = "&BC29"
    SCR_INK_ENCODE      = "&BC2C"
    SCR_INK_DECODE      = "&BC2F"
    SCR_SET_INK         = "&BC32"
    SCR_GET_INK         = "&BC35"
    SCR_SET_BORDER      = "&BC38"
    SCR_GET_BORDER      = "&BC3B"
    SCR_SET_FLASHING    = "&BC3E"
    SCR_GET_FLASHING    = "&BC41"
    SCR_FILL_BOX        = "&BC44"
    SCR_FLOOD_BOX       = "&BC17"
    SCR_CHAR_INVERT     = "&BC4A"
    SCR_HW_ROLL         = "&BC4D"
    SCR_SW_ROLL         = "&BC50"
    SCR_UNPACK          = "&BC53"
    SCR_REPACK          = "&BC56"
    SCR_ACCESS          = "&BC59"
    SCR_PIXELS          = "&BC5C"
    SCR_HORIZONTAL      = "&BC5F"
    SCR_VERTICAL        = "&BC62"
    
    # WATCH OUT: this are 464 addresses
    MATH_MOVE_REAL      = "&BD3D"
    MATH_INT_TO_REAL    = "&BD40"
    MATH_BIN_TO_REAL    = "&BD43"
    MATH_REAL_TO_INT    = "&BD46"
    MATH_REAL_TO_BIN    = "&BD49"
    MATH_REAL_FIX       = "&BD4C"
    MATH_REAL_INT       = "&BD4F"
    MATH_REAL_10A       = "&BD55"
    MATH_REAL_ADD       = "&BD58"
    MATH_REAL_REV_SUBS  = "&BD5E"
    MATH_REAL_MULT      = "&BD61"
    MATH_REAL_DIV       = "&BD64"
    MATH_REAL_COMP      = "&BD6A"
    MATH_REAL_UMINUS    = "&BD6D"
    MATH_REAL_SIGNUM    = "&BD70"
    MATH_SET_ANGLE_MODE = "&BD73"
    MATH_REAL_PI        = "&BD76"
    MATH_REAL_SQR       = "&BD79"
    MATH_REAL_POWER     = "&BD7C"
    MATH_REAL_LOG       = "&BD7F"
    MATH_REAL_LOG_10    = "&BD82"
    MATH_REAL_EXP       = "&BD85"
    MATH_REAL_SINE      = "&BD88"
    MATH_REAL_COSINE    = "&BD8B"
    MATH_REAL_TANGENT   = "&BD8E"
    MATH_REAL_ARCTANGENT= "&BD91"
#
# Utility routines and libraries
#

STRLIB = {
    "strlib_print_nl": [
        "strlib_print_nl:\n",
        "\tld      a,13\n",
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tld      a,10\n",
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tret\n\n"
    ],
    "strlib_print_spc": [
        "; HL indicates the number of spaces to print\n",
        "; but 127 is the maximum\n",
        "strlib_print_spc:\n",
        "\tld      a,l\n",
        "\tand     &7F\n",
        "\tld      b,a\n",
        "\tld      a,32   ; white space\n",
        "__print_spc_loop:"
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tdjnz    __print_spc_loop\n",
        "\tret\n\n"
    ],
    "strlib_print_str": [
        "; HL = address to the string to print\n",
        "strlib_print_str:\n",
        "\tld      a,(hl)\n",
        "\tor      a\n",
        "\tret     z\n",
        "\tinc     hl\n",
        f"\tcall    {FWCALL.TXT_OUTPUT}\n",
        "\tjr      strlib_print_str\n\n"
    ],
    "strlib_dropspaces": [
        "; DE points to the string\n",
        "; DE ends pointing to end of char or character <> ' '\n"
        "strlib_dropspaces:\n",
        "\tld      a,(de)\n",
        "\tcp      &20     ; white space\n",
        "\tret     nz\n",
        "\tinc     de\n",
        "\tjr      strlib_dropspaces\n"
    ],
    "strlib_copy": [
        "; HL = destination\n",
        "; DE = origin\n",
        "strlib_strcopy:\n",
        "\tld      a,(de)\n",
        "\tld      (hl),a\n",
        "\tinc     hl\n",
        "\tinc     de\n",
        "\tor      a\n",
        "\tjr      nz,strlib_strcopy\n",
        "\tret\n\n",
    ],
    "strlib_comp": [
        "; HL = second string start\n",
        "; DE = first string start\n",
        "strlib_strcomp:\n",
        "\tld      a,(de)\n",
        "\tcp      (hl)     ; lets keep A untouched\n",
        "\tjr      nz,__strlib_strcomp_false\n",
        "\tor      (hl)\n",
        "\tcp      0\n",
        "\tjr      z,__strlib_strcomp_true\n",
        "\tinc     hl\n",
        "\tinc     de\n",
        "\tjr      strlib_strcomp\n",
        "__strlib_strcomp_true\n",
        "\tld      hl,&FFFF  ; HL =-1 (true) they are equal\n",
        "\tret\n",
        "__strlib_strcomp_false:\n"
        "\tld      hl,0    ; HL = 0 (false) they are different\n", 
        "\tret\n"
    ],
    "strlib_int2str": [
        "; HL = starts with the number to convert to string\n",
        "; DE = memory address to convertion buffer\n",
        "; HL ends storing the memory address to the buffer\n",
        "; subroutine taken from https://wikiti.brandonw.net/index.php?title=Z80_Routines:Other:DispA\n",
        "strlib_int2str:\n",
        "\tld      de,__strlib_int2str_conv\n"
        "\t; Detect sign of HL\n",
        "\tbit     7, h\n",
        "\tjr      z, __strlib_int2str_convert0\n",
        "\t; HL is negative so add '-' to string and negate HL\n"
        '\tld      a,"-"\n',
        "\tld      (de), a\n",
        "\tinc     de\n",
        "\t; Negate HL (using two's complement)\n",
        "\txor     a\n",
        "\tsub     l\n",
        "\tld      l, a\n",
        "\tld      a, 0   ; Note that XOR A or SUB A would disturb CF\n",
        "\tsbc     a, h\n",
        "\tld      h, a\n",
        "__strlib_int2str_convert0:\n",
        "\t; Convert HL to digit characters\n",
        "\tld      b,0    ; B will count character length of number\n",
        "__strlib_int2str_convert1:\n",
        "\tpush    bc\n",
        "\tcall    div16_hlby10 ; HL = HL / A, A = remainder\n",
        "\tpop     bc\n",
        "\tpush    af     ; Store digit in stack\n",
        "\tinc     b\n",
        "\tld      a,h\n",
        "\tor      l      ; End of string?\n",
        "\tjr      nz, __strlib_int2str_convert1\n",
        "__strlib_int2str_convert2:\n",
        "\t; Retrieve digits from stack\n",
        "\tpop     af\n",
        "\tor      &30    ; '0' + A\n",
        "\tld      (de), a\n",
        "\tinc     de\n",
        "\tdjnz    __strlib_int2str_convert2\n",
        "\t; Terminate string with NULL\n",
        "\txor     a      ; clear flags\n",
        "\tld      (de), a\n",
        "\tld      hl,__strlib_int2str_conv\n",
        "\tret\n",
    ],
    "strlib_str2int": [
        "; DE points to the string, ends pointing to the next char not processed\n",
        "; HL points to de memory where to store the integer\n",
        "; A is the 8-bit value of the number\n",
        "; Routine based in the library created by Zeda:\n",
        "; https://github.com/Zeda/Z80-Optimized-Routines\n",
        "strlib_str2int:\n",
        "\tpush    hl\n"
        "\tld      hl,0\n",
        "__strlib_str2int_loop:\n",
        "\tld      a,(de)\n",
        "\tsub     &30  ; '0' character\n",
        "\tcp      10\n",
        "\tjr      nc,__strlib_str2int_end\n",
        "\tinc     de\n",
        "\tld      b,h\n",
        "\tld      c,l\n",
        "\tadd     hl,hl  ; x2\n",
        "\tadd     hl,hl  ; x4\n",
        "\tadd     hl,bc  ; x5\n",
        "\tadd     hl,hl  ; x10\n",
        "\tadd     a,l\n",
        "\tld      l,a\n",
        "\tjr      nc,__strlib_str2int_loop\n",
        "\tinc     h\n",
        "\tjp      __strlib_str2int_loop\n"
        "__strlib_str2int_end:\n"
        "\tld      b,h\n",
        "\tld      c,l\n",
        "\tpop     hl\n",
        "\tld      (hl),c\n",
        "\tinc     hl\n",
        "\tld      (hl),b\n",
        "\tret\n",
    ],
    "strlib_int2hex": [
        "; HL = destination memory address\n",
        "; A  = number of characters: 2 or 4\n",
        "; DE = Number to convert to hex string\n",
        "; Routine taken initially from book 'Ready Made Machine Language Routines'\n",
        "strlib_int2hex:\n",
        "\tpush    hl\n",
        "\tcp      2\n",
        "\tjr      z,__strlib_int2hex_low\n",
        "\tld      a,d\n",
        "\tcall    __strlib_a2hex\n",
        "__strlib_int2hex_low:\n",
        "\tld      a,e\n",
        "\tcall    __strlib_a2hex\n",
        "\tpop     hl\n",
        "\tret\n",
        "__strlib_a2hex:\n",
        "\tld      b,2    ; b=0 marks the end\n",
        "\tld      c,a    ; original number\n",
        "\trr      a      ; move high order bits\n",
        "\trr      a      ; into the low part\n",
        "\trr      a\n",
        "\trr      a\n",
        "__strlib_a2hex_conv:\n",
        "\tand     &0F\n",
        "\tcp      &0A    ; check if is greater or equal\n",
        "\tjr      nc,__strlib_a2hex_letter\n",
        "\tadd     a,&30  ; get the number ASCII code\n",
        "\tjr      __strlib_a2hex_store\n",
        "__strlib_a2hex_letter:\n",
        "\tadd     a,&37\n",
        "__strlib_a2hex_store:\n",
        "\tld      (hl),a\n",
        "\tinc     hl\n",
        "\tdec     b\n",
        "\tjr      z,__strlib_a2hex_end\n",
        "\tld      a,c\n",
        "\tjr      __strlib_a2hex_conv\n",
        "__strlib_a2hex_end:\n",
        "\tld      (hl),0\n",
        "\tret\n",
    ],
}

INPUTLIB = {
    "inputlib_input": [
        "inputlib_input:\n",
        f"\tcall    {FWCALL.TXT_CUR_ENABLE} ; TXT_CUR_ENABLE\n",
        f"\tcall    {FWCALL.TXT_CUR_ON} ; TXT_CUR_ON\n",
        "\tld      hl,__inputlib_inbuf\n",
        "\tld      bc,0  ; Initialize characters counter\n",
        "__input_enterchar:\n",
        f"\tcall    {FWCALL.KM_WAIT_KEY} ; KM_WAIT_KEY\n",
        "\tcp      127  ; above call returns characters in range &00-&7F\n",
        "\tjr      nz,__input_checkenter\n",
        "\tld      a,b\n",
        "\tor      c\n",
        "\tjr      z,__input_enterchar    ; String length is zero\n",
        "\tld      a,8\n",
        f"\tcall    {FWCALL.TXT_OUTPUT} ; TXT_OUTPUT\n",
        '\tld      a," "\n',
        f"\tcall    {FWCALL.TXT_OUTPUT} ; TXT_OUTPUT\n",
        "\tld      a,8\n",
        f"\tcall    {FWCALL.TXT_OUTPUT} ; TXT_OUTPUT\n",
        "\tdec     hl\n",
        "\tdec     bc\n",
        "\tjr      __input_enterchar\n",
        "__input_checkenter:\n",
        "\tcp      13\n",
        "\tjr      z,__input_end    ; Enter key pressed\n",
        f"\tcall    {FWCALL.TXT_OUTPUT} ; TXT_OUTPUT\n",
        "\tld      (hl),a\n",
        "\tinc     hl\n",
        "\tinc     bc\n",
        "\tjr      __input_enterchar\n",
        "__input_end:\n",
        "\txor     a\n",
        "\tld      (hl),a\n",
        "\tcall    strlib_print_nl  ; Print enter character\n",
        f"\tcall    {FWCALL.TXT_CUR_DISABLE} ; TXT_CUR_DISABLE\n",
        f"\tjp      {FWCALL.TXT_CUR_OFF} ; TXT_CUR_OFF its ret will work as input ret\n",
    ],
}

MATHLIB = {
    "mult16_unsigned": [
        "; 16x16 unsigned multplication, HL = HL*DE.\n",
        "; Algorithm from Rodney Zaks, 'Programming the Z80'.\n",
        "; Developed by Nils M. Holm (cc0)\n",
        "mul16_unsigned:\n",
        "\tld      a,l	; transfer HL to CA\n",
        "\tld      c,h\n",
        "\tld      b,16	; 16 bits to multiply\n",
        "\tld      hl,0\n",
        "mul0_unsigned:\n",
        "\tsrl     c		; shift CA right, get low bit\n",
        "\trra\n",
        "\tjr      nc,mul1_unsigned	; zero fell out, do not add\n",
        "\tadd     hl,de	; else add DE\n",
        "mul1_unsigned:\n",
        "\tex      de,hl	; DE = DE*2\n",
        "\tadd     hl,hl\n",
        "\tex      de,hl\n",
        "\tdjnz    mul0_unsigned\n",
        "\tret\n",
    ],
    "div16_unsigned": [
        "; 16/16 unsigned division, HL = HL div DE, DE = HL mod DE.\n",
        "; Algorithm from Rodney Zaks, 'Programming the Z80'.\n",
        "; Developed by Nils M. Holm (cc0)\n",
        "div16_unsigned:\n",
        "\tld      a,h	; transfer HL to AC\n",
        "\tld      c,l\n",
        "\tld      hl,0	; intermediate result\n",
        "\tld      b,16	; 16 bits to divide\n",
        "div0_unsigned:\n",
        "\trl      c		; get AC high bit, rotate in result bit\n",
        "\trla\n",
        "\tadc     hl,hl	; HL = HL*2, never sets C\n",
        "\tsbc     hl,de	; trial subtract and test DE > HL\n",
        "\tjr      nc,div1_unsigned\n",
        "\tadd     hl,de	; DE > HL, restore HL\n",
        "div1_unsigned:\n",
        "\tccf		; result bit\n",
        "\tdjnz    div0_unsigned\n",
        "\trl      c		; rotate in last result bit\n",
        "\trla\n",
        "\tld      d,a\n",
        "\tld      e,c\n",
        "\tex      de,hl\n",
	    "\tret\n",
    ],
    "sign_extract": [
        "; extract common sign from two mul/div factors (HL, DE);\n",
        "; return CY=0, if signs are equal and otherwise CY=1\n",
        "; Developed by Nils M. Holm (cc0)\n",
        "sign_extract:\n",
        "\tld      a,h\n",
        "\txor     d\n",
        "\trla		; sign to carry\n",
        "\tret\n",
    ],
    "sign_strip": [    
        "; strip signs from HL and DE\n",
        "sign_strip:\n",
        "\tbit     7,d\n",
        "\tjr      z,sb0\n",
        "\tld      a,d\n",
        "\tcpl\n",
        "\tld      d,a\n",
        "\tld      a,e\n",
        "\tcpl\n",
        "\tld      e,a\n",
        "\tinc     de\n",
        "sb0:\n",
        "\tbit     7,h\n",
        "\tret     z\n",
        "neghl:\n",
        "\tld      a,h\n",
        "\tcpl\n",
        "\tld      h,a\n",
        "\tld      a,l\n",
        "\tcpl\n",
        "\tld      l,a\n",
        "\tinc     hl\n",
        "\tret\n",
    ],
    "mult16_signed": [
        "; 15x15 signed multiplication\n",
        "mul16_signed:\n",	
        "\tcall    sign_extract\n",
        "\tpush    af\n",
        "\tcall    sign_strip\n",
        "\tcall    mul16_unsigned\n",
        "\tpop     af\n",
        "\tret     nc\n",
        "\tjr      neghl\n",
    ],
    "div16_signed": [
        "; 15/15 signed division\n",
        "div16_signed:\n",
        "\tex      de,hl\n",
        "\tcall    sign_extract\n",
        "\tpush    af\n",
        "\tcall    sign_strip\n",
        "\tcall    div16_unsigned\n",
        "\tpop     af\n",
        "\tret     nc\n",
        "\tjr      neghl\n",
    ],
    "mod16": [
        "; 15/15 unsigned remainder\n",
        "mod16:\n",
        "\tex      de,hl\n",
        "\tcall    div16_unsigned\n",
        "\tex      de,hl\n",
        "\tret\n",
    ],
    "comp16_signed": [
        "; signed comparison HL-DE, set Z and CY flags,\n",
        "; where CY indicates that HL < DE\n",
        "comp16_signed:\n",
        "\txor     a\n",
        "\tsbc     hl,de\n",
        "\tret     z\n",
        "\tjp      m,cs1\n",
        "\tor      a\n",
        "\tret\n",
        "cs1:\n",
        "\tscf\n",
        "\tret\n",
    ],
    "comp16_unsigned": [
        "comp16_unsigned:\n",
        "\txor     a\n",
        "\tsbc     hl,de\n",
        "\tret\n",
    ],
    "div16_hlby10": [
        ";Taken from https://learn.cemetech.net/index.php/Z80:Math_Routines&Speed_Optimised_HL_div_10\n",
        ";Inputs:\n",
        ";     HL\n",
        ";Outputs:\n",
        ";     HL is the quotient\n",
        ";     A is the remainder\n",
        ";     DE is not changed\n",
        ";     BC is 10\n",
        "div16_hlby10:\n",
        "\tld      bc,&0D0A\n",
        "\txor     a\n",
        "\tadd     hl,hl\n",
        "\trla\n",
        "\tadd     hl,hl\n",
        "\trla\n",
        "\tadd     hl,hl\n",
        "\trla\n",
        "\tadd     hl,hl\n",
        "\trla\n",
        "\tcp      c\n",
        "\tjr      c,$+4\n",
        "\tsub     c\n",
        "\tinc     l\n",
        "\tdjnz    $-7\n",
        "\tret\n",
    ],
}
