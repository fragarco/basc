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
from bastypes import BASTypes, SymbolTable

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

    def emitlibcode(self, code: str) -> None:
        self.libcode.append(code + '\n')

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
                self.emitdata(f'{symbol.symbol}: dw 0')
            elif symbol.valtype == BASTypes.REAL:
                self.emitdata(f'{symbol.symbol}: dw 0,0')
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

    def emit_rtcall(self, fun: str) -> None:
        fun_cb = getattr(self, "rtcall_" + fun, None)
        if fun_cb is None:
            self.abort(f"{fun} call is not implemented yet")
        else:
            fun_cb()

    def _addcode(self, line: str) -> None:
        self.code.append(line + '\n')

    def _addlibfunc(self, lib: Any, fname: str) -> bool:
        if fname not in self.libs:
            self.libs.append(fname)
            fcode: List[str] = lib[fname]
            self.libcode = self.libcode + fcode
            return True
        return False

    def rtcall_CHANNEL_SET(self) -> None:
        # 0-7 keyboard to screen
        # 8   keyboard to printer
        # 9   channel to file
        self._addcode("\tld      a,l")
        self._addcode("\tand     &0F   ;valid stream range 0-9")
        self._addcode(f"\tcall    {FWCALL.TXT_STR_SELECT} ;TXT_STR_SELECT")

    def rtcall_CLS(self) -> None:
        self._addcode(f"\tcall    {FWCALL.TXT_CLEAR_WINDOW} ;TXT_CLEAR_WINDOW")

    def rtcall_END(self) -> None:
        self._addcode("\tjp      0  ; reset")

    def rtcall_INKEYS(self) -> None:
        self._addcode(f"\tcall    {FWCALL.KM_READ_CHAR} ;KM_READ_CHAR")
        self._addcode("\tjr      c,@+3  ; if not character then A=0")
        self._addcode("\txor     a")
        self._addcode("\tpop     hl     ; destination address")
        self._addcode("\tld      (hl),a")
        self._addcode("\tinc     hl")
        self._addcode("\tld      (hl),&00")

    def rtcall_MODE(self) -> None:
        self._addcode("\tpush    af")
        self._addcode("\tld      a,l")
        self._addcode(f"\tcall    {FWCALL.SCR_SET_MODE} ;SCR_SET_MODE")
        self._addcode("\tpop     af")

    def rtcall_PRINT(self) -> None:
        self._addlibfunc(STRLIB, "strlib_print_str")
        self._addcode("\tcall    strlib_print_str")

    def rtcall_PRINT_LN(self) -> None:
        self._addlibfunc(STRLIB, "strlib_print_nl")
        self._addcode("\tcall    strlib_print_nl")

    def rtcall_PRINT_INT(self) -> None:
        self._addlibfunc(MATHLIB, "div16_hlby10")
        if self._addlibfunc(STRLIB, "strlib_int2str"):
            self.emitdata('__strlib_int2str_conv: defs 7')
        self._addcode("\tcall    strlib_int2str")
        self.rtcall_PRINT()

    def rtcall_PRINT_REAL(self) -> None:
        self.abort("PRINT does not support REAL expressions yet")
    
    def rtcall_STRCOMP(self) -> None:
        self._addlibfunc(STRLIB, "strlib_comp")
        self._addcode("\tpop     de")
        self._addcode("\tcall    strlib_strcomp")

    def rtcall_STRCOPY(self) -> None:
        self._addlibfunc(STRLIB, "strlib_copy")
        self._addcode("\tpop     de")
        self._addcode("\tcall    strlib_strcopy")

    def rtcall_INPUT(self) -> None:
        if self._addlibfunc(INPUTLIB, "inputlib_input"):
            self.emitdata('__inputlib_question: db "?",&0')
            self.emitdata('__inputlib_redo: db "?Redo from start",&0')
            self.emitdata('__inputlib_inbuf: defs 256')
        self._addlibfunc(STRLIB, "strlib_copy")
        self._addcode("\tpush    hl")
        self._addcode("\tcall    inputlib_input")
        self._addcode("\tpop     de")
        self._addcode("\tld      b,e   ; number of pushed variables")
        self._addcode("\tex      de,hl")
        self._addcode("__input_assign_values:")
        self._addcode("\tpop     hl")
        self._addcode("\tcall    strlib_strcopy")
        self._addcode("\tdjnz    __input_assign_values")
