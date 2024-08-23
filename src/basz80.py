"""
Translates intermediate code generated by the Emitter object
to Amstrad CPC Z80 Assembly language in Maxam/WinAPE style.

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

import sys
from typing import List, Optional, Tuple, Any
from basz80lib import SM2Z80, FWCALL, STRLIB, MATHLIB, INPUTLIB
from bastypes import BASTypes, SymbolTable, Symbol

class Z80Backend:
    """
    Generates code for Amstrad CPC in Z80 Assembly language (Maxam/WinAPE style)
    """

    def __init__(self) -> None:
        self.symbols: Optional[SymbolTable] = None
        self.libs: List[str] = []
        self.icode: List[Tuple[str, str, str]] = []
        self.libcode: List[str] = ["\n","; LIBRARY AREA\n", "\n"]  # reusable and utility asm subroutines
        self.code: List[str] = []                                  # program code
        self.data: List[str] = ["\n","; DATA AREA\n", "\n"]        # data/constants declaration area    

    def abort(self, message: str) -> None:
        print(f"Fatal error: {message}")
        sys.exit(1)

    def _real(self, number: str) -> bytearray:
        """
        In Amstrad BASIC, a floating point number is stored in base-2 in a normalized form 1 x 2 ** <exp>
        The representation uses 5 bytes stored using the following structure:
        | M (31-24) | M	(23-16) | M	(15-8) | sign + M (7-0) | exponent |
        The exponent is 8-bit an uses a bias of 128 (128-255 possitive, 0-127 negative)
        """
        n = float(number)
        sign = '1' if n < 0 else '0'
        exp = 0
        prec = abs(n)
    
        while prec >= 1:
            exp = exp + 1
            prec = prec / 2.0
        while 0 < prec < 0.5:
            prec = prec * 2
            exp = exp - 1

        exp = 0 if exp == 0 else exp + 128
        bit = 0
        mant = ""
        for i in range(32):
            prec = prec - bit
            prec = prec * 2
            bit = int(prec)
            mant = mant + str(bit)
        # round values last bit
        if prec > 0.5: mant = mant[:-1] + '1'
        # is normalized so drop first bit and used it for sign
        mant = sign + mant[1:]
        real = bytearray(int(mant, 2).to_bytes(4, byteorder='little'))
        real.extend(exp.to_bytes())
        return real

    def _emitrealsym(self, sym: Symbol) -> None:
        codedreal = bytearray(0 for i in range(5))
        if sym.is_constant() and sym.is_tmp():
            codedreal = self._real(sym.value[0][0].text)
        code = f'{sym.symbol}: db '
        for b in codedreal:
            code = code + f'&{b:02X},'
        # send code without last ','
        self.emitdata(code[:-1])

    def _addcode(self, line: str) -> None:
        self.code.append(line + '\n')

    def _addlibfunc(self, lib: Any, fname: str) -> bool:
        if fname not in self.libs:
            self.libs.append(fname)
            fcode: List[str] = lib[fname]
            self.libcode = self.libcode + fcode
            return True
        return False

    def _emitauxcode(self, inst: str) -> None:
        if inst == "MUL" or inst == "UMUL":
            self._addlibfunc(MATHLIB, "mult16_unsigned")
            self._addlibfunc(MATHLIB, "sign_extract")
            self._addlibfunc(MATHLIB, "sign_strip")
            self._addlibfunc(MATHLIB, "mult16_signed")
        elif inst == "DIV" or inst == "UDIV":
            self._addlibfunc(MATHLIB, "div16_unsigned")
            self._addlibfunc(MATHLIB, "sign_extract")
            self._addlibfunc(MATHLIB, "sign_strip")
            self._addlibfunc(MATHLIB, "div16_signed")
        elif inst == "MOD":
            self._addlibfunc(MATHLIB, "div16_unsigned")
            self._addlibfunc(MATHLIB, "mod16")
        elif inst in ["LT", "GT", "LE", "GE"]:
            self._addlibfunc(MATHLIB, "comp16_signed")
            self._addlibfunc(MATHLIB, "comp16_unsigned")
    
    def emitlibcode(self, code: str) -> None:
        self.libcode.append(code + '\n')
    
    def emitcode(self, inst: str, arg: str, prefix: str) -> None:
        if inst == "LIBCALL":
            # BASIC original function
            self.emit_rtcall(arg)
        elif inst in SM2Z80:
            self._emitauxcode(inst)
            code: List[str] = SM2Z80[inst]
            for line in code:
                if arg != '': line = line.replace('$ARG1', arg)
                self.code.append(prefix + line + '\n')
        else:
            self.abort(f"intermediate op-code {inst} is unknown")

    def emitdata(self, code: str) -> None:
        self.data.append(code + '\n')

    def emit_rtcall(self, fun: str) -> None:
        fun_cb = getattr(self, "rtcall_" + fun, None)
        if fun_cb is None:
            self.abort(f"{fun} call is not implemented yet")
        else:
            fun_cb()

    def generatecode(self, orgaddr: int) -> None:
        self.code.append('org &%04X\n' % orgaddr)
        self.code = self.code + ["\n","; CODE AREA\n", "\n"]

        for inst, arg, prefix in self.icode:
            self.emitcode(inst, arg, prefix)

    def generatesymbols(self) -> None:
        assert self.symbols is not None
        for symname in self.symbols.getsymbols():
            symbol = self.symbols.get(symname)
            if symbol.valtype == BASTypes.INT:
                self.emitdata(f'{symbol.symbol}: dw &00')
            elif symbol.valtype == BASTypes.REAL:
                self._emitrealsym(symbol)
            elif symbol.valtype == BASTypes.STR:
                if symbol.is_constant() and symbol.is_tmp():
                    self.emitdata(f'{symbol.symbol}: db "{symbol.value[0][0].text}",&00')
                else:    
                    self.emitdata(f'{symbol.symbol}: defs 256')
            else:
                # This symbol is a label that was processed by LABEL instruction
                pass

    def save_output(self, outputfile: str, icode: List[Tuple[str, str, str]], symbols: SymbolTable, startaddr = 0x4000):
        """
        outputfile: output file where assembly code will be written
        icode: Intermediate code generated by the Emitter
        symbols: SymbolTable generated by the parser
        startaddr: Starting memory position for the code generated
        """
        self.symbols = symbols
        self.icode = icode
        self.generatesymbols()
        self.generatecode(startaddr)
        with open(outputfile, "w") as fd:
            fd.writelines(self.code)
            fd.writelines(self.libcode)
            fd.writelines(self.data)

    # BASIC commands and functions

    def rtcall_ASC(self) -> None:
        self._addcode("\t; ASC")
        self._addcode("\tpop     de      ; destination int var")
        self._addcode("\tld      a,(hl)  ; get first char")
        self._addcode("\tld      (de),a")
        self._addcode("\t;")

    def rtcall_BORDER(self) -> None:
        self._addcode("\t; BORDER")
        self._addcode("\tld      c,l     ; second color")
        self._addcode("\tpop     de")
        self._addcode("\tld      b,e     ; first color")
        self._addcode(f"\tcall    {FWCALL.SCR_SET_BORDER} ;SCR_SET_BORDER")
        self._addcode("\t;")

    def rtcall_CHANNEL_SET(self) -> None:
        # 0-7 keyboard to screen
        # 8   keyboard to printer
        # 9   channel to file
        self._addcode("\t; CHANNEL SET")
        self._addcode("\tld      a,l")
        self._addcode("\tand     &0F   ;valid stream range 0-9")
        self._addcode(f"\tcall    {FWCALL.TXT_STR_SELECT} ;TXT_STR_SELECT")
        self._addcode("\t;")

    def rtcall_CHRS(self) -> None:
        self._addcode("\t; CHR$")
        self._addcode("\tpop     de     ; destination buffer")
        self._addcode("\tex      de,hl  ; store char number in e")
        self._addcode("\tld      (hl),e")
        self._addcode("\tinc     hl") 
        self._addcode("\tld      (hl),&00")
        self._addcode("\t;")

    def rtcall_CLS(self) -> None:
        self._addcode("\t; CLS")
        self._addcode(f"\tcall    {FWCALL.TXT_CLEAR_WINDOW} ;TXT_CLEAR_WINDOW")
        self._addcode("\t;")

    def rtcall_END(self) -> None:
        self._addcode("\t; END")
        self._addcode("\tjp      0  ; reset")
        self._addcode("\t;")

    def rtcall_FRAME(self) -> None:
        self._addcode("\t; FRAME")
        self._addcode("\tcall    &BD19 ; MC_WAIT_FLYBACK / WAIT VSYNC")
        self._addcode("\t;")

    def rtcall_HEXS(self) -> None:
        self._addcode("\t; HEX$")
        self._addlibfunc(STRLIB, "strlib_int2hex")
        # the second parameters is ignored right now
        self._addcode("\tld      a,l    ; number of characters only 2 or 4 are supported")
        self._addcode("\tpop     de     ; number to convert")
        self._addcode("\tpop     hl     ; destination buffer")
        self._addcode("\tcall    strlib_int2hex")
        self._addcode("\t;")

    def rtcall_INK(self) -> None:
        self._addcode("\t; INK")
        self._addcode("\tld      c,l     ; second color")
        self._addcode("\tpop     de")
        self._addcode("\tld      b,e     ; first color")
        self._addcode("\tpop     de")
        self._addcode("\tld      a,e     ; pen")
        self._addcode(f"\tcall    {FWCALL.SCR_SET_INK} ;SCR_SET_INK")
        self._addcode("\t;")

    def rtcall_INKEYS(self) -> None:
        self._addcode("\t; INKEY$")
        self._addcode(f"\tcall    {FWCALL.KM_READ_CHAR} ;KM_READ_CHAR")
        self._addcode("\tjr      c,$+3  ; if not character then A=0")
        self._addcode("\txor     a")
        self._addcode("\tpop     hl     ; destination address")
        self._addcode("\tld      (hl),a")
        self._addcode("\tinc     hl")
        self._addcode("\tld      (hl),&00")
        self._addcode("\t;")

    def rtcall_INPUT(self) -> None:
        self._addcode("\t; INPUT")
        if self._addlibfunc(INPUTLIB, "inputlib_input"):
            self.emitdata('__inputlib_question: db "?"," ",&0')
            self.emitdata('__inputlib_redo: db "?Redo from start",&0')
            self.emitdata('__inputlib_inbuf: defs 256')
        self._addcode("\tcall    inputlib_input")
        self._addcode("\tld      de,__inputlib_inbuf")
        self._addcode("\t;")

    def rtcall_INPUT_INT(self) -> None:
        self._addcode("\t; INPUT_INT")
        self._addlibfunc(STRLIB, "strlib_dropspaces")
        self._addlibfunc(STRLIB, "strlib_str2int")
        self._addcode("\tcall    strlib_dropspaces")
        self._addcode("\tcall    strlib_str2int")
        self._addcode("\t;")

    def rtcall_INPUT_REAL(self) -> None:
        self._addcode("\t; INPUT_REAL")
        self._addlibfunc(STRLIB, "strlib_dropspaces")
        self._addcode("\tcall    strlib_dropspaces")
        self.abort("INPUT does not support REAL variables yet")
        self._addcode("\t;")

    def rtcall_INPUT_STR(self) -> None:
        self._addcode("\t; INPUT_STR")
        self._addlibfunc(STRLIB, "strlib_dropspaces")
        self._addlibfunc(STRLIB, "strlib_copy")
        self._addcode("\tcall    strlib_dropspaces")
        self._addcode("\tcall    strlib_strcopy")
        self._addcode("\t;")

    def rtcall_MODE(self) -> None:
        self._addcode("\t; MODE")
        self._addcode("\tpush    af")
        self._addcode("\tld      a,l")
        self._addcode(f"\tcall    {FWCALL.SCR_SET_MODE} ;SCR_SET_MODE")
        self._addcode("\tpop     af")
        self._addcode("\t;")

    def rtcall_LOCATE(self) -> None:
        self._addcode("\t; LOCATE")
        self._addcode("\tpop     de")
        self._addcode("\tld      h,e")
        self._addcode(f"\tcall    {FWCALL.TXT_SET_CURSOR} ;TXT_SET_CURSOR")
        self._addcode("\t;")

    def rtcall_PAPER(self) -> None:
        self._addcode("\t; PAPER")
        self._addcode("\tld      a,l     ; color")
        self._addcode(f"\tcall    {FWCALL.TXT_SET_PAPER} ;TXT_SET_PAPER")
        self._addcode("\t;")

    def rtcall_PEEK(self) -> None:
        # HL contains the memory we want to read
        self._addcode("\t; PEEK")
        self._addcode("\tld      a,(hl)")
        self._addcode("\tpop     hl")
        self._addcode("\tld      (hl),a")
        self._addcode("\t;")

    def rtcall_PEN(self) -> None:
        self._addcode("\t; PEN")
        self._addcode("\tld      a,l     ; color")
        self._addcode(f"\tcall    {FWCALL.TXT_SET_PEN} ;TXT_SET_PEN")
        self._addcode("\t;")

    def rtcall_PRINT(self) -> None:
        self._addcode("\t; PRINT")
        self._addlibfunc(STRLIB, "strlib_print_str")
        self._addcode("\tcall    strlib_print_str")
        self._addcode("\t;")

    def rtcall_PRINT_INT(self) -> None:
        self._addcode("\t; PRINT_INT")
        self._addlibfunc(MATHLIB, "div16_hlby10")
        if self._addlibfunc(STRLIB, "strlib_int2str"):
            self.emitdata('__strlib_int2str_conv: defs 7')
        self._addcode("\tcall    strlib_int2str")
        self._addcode("\t;")
        self.rtcall_PRINT()
        

    def rtcall_PRINT_LN(self) -> None:
        self._addcode("\t; PRINT_LN")
        self._addlibfunc(STRLIB, "strlib_print_nl")
        self._addcode("\tcall    strlib_print_nl")
        self._addcode("\t;")

    def rtcall_PRINT_QM(self) -> None:
        """ print a question mark and a space """
        self._addcode("\t; PRINT_QM")
        self._addcode("\tld      hl,__inputlib_question")
        self.rtcall_PRINT()
        self._addcode("\t;")

    def rtcall_PRINT_REAL(self) -> None:
        self._addcode("\t; PRINT_REAL")
        self.abort("PRINT does not support REAL expressions yet")
        self._addcode("\t;")

    def rtcall_PRINT_SPC(self) -> None:
        self._addcode("\t; PRINT_SPC")
        self._addlibfunc(STRLIB, "strlib_print_spc")
        self._addcode("\tcall    strlib_print_spc")
        self._addcode("\t;")

    def rtcall_REALCOPY(self) -> None:
        self._addcode("\t; REALCOPY")
        self._addcode("\tpop     de")
        self._addcode("\tex      de,hl")
        self._addcode("\tld      bc,5")
        self._addcode("\tldir")
        self._addcode("\t;")

    def rtcall_STRCOMP(self) -> None:
        self._addcode("\t; STRCOMP")
        self._addlibfunc(STRLIB, "strlib_comp")
        self._addcode("\tpop     de")
        self._addcode("\tcall    strlib_strcomp")
        self._addcode("\t;")

    def rtcall_STRCOPY(self) -> None:
        self._addcode("\t; STRCOPY")
        self._addlibfunc(STRLIB, "strlib_copy")
        self._addcode("\tpop     de")
        self._addcode("\tcall    strlib_strcopy")
        self._addcode("\t;")

    def rtcall_STRCAT(self) -> None:
        self._addcode("\t; STRCAT")
        self._addlibfunc(STRLIB, "strlib_len")
        self._addlibfunc(STRLIB, "strlib_copy")
        self._addlibfunc(STRLIB, "strlib_cat")
        self._addcode("\tpop     de")
        self._addcode("\tex      de,hl")
        self._addcode("\tcall    strlib_strcat")
        self._addcode("\t;")
