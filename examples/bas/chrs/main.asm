org &4000

; CODE AREA

; 10 ' CHR$ Example of use
__label_line_10:
; 20 mode 2
__label_line_20:
	ld      hl,2
	; MODE
	push    af
	ld      a,l
	call    &BC0E ;SCR_SET_MODE
	pop     af
	;
; 30 for x=32 to 255
__label_line_30:
	ld      hl,32
	ld      (var_x),hl
	ld      hl,255
	ld      (var_tmp000),hl
label_001:
	ld      hl,(var_x)
	push    hl
	ld      hl,(var_tmp000)
	pop     de
	xor     a
	sbc     hl,de
	jp      c,label_002
; 40 print x;" ";chr$(x);" ";
__label_line_40:
	ld      hl,0
	; CHANNEL SET
	ld      a,l
	and     &0F   ;valid stream range 0-9
	call    &BBB4 ;TXT_STR_SELECT
	;
	ld      hl,(var_x)
	; PRINT_INT
	call    strlib_int2str
	;
	; PRINT
	call    strlib_print_str
	;
	ld      hl,var_tmp003
	; PRINT
	call    strlib_print_str
	;
	ld      hl,var_tmp004
	push    hl
	ld      hl,(var_x)
	; CHR$
	pop     de     ; destination buffer
	ex      de,hl  ; store char number in e
	ld      (hl),e
	inc     hl
	ld      (hl),&00
	;
	ld      hl,var_tmp004
	; PRINT
	call    strlib_print_str
	;
	ld      hl,var_tmp005
	; PRINT
	call    strlib_print_str
	;
; 50 next
__label_line_50:
	ld      hl,(var_x)
	inc     hl
	ld      (var_x),hl
	jp      label_001
label_002:
; 60 loop:
__label_line_60:
LOOP:
; 70 goto loop
__label_line_70:
	jp      LOOP

; LIBRARY AREA

;Taken from https://learn.cemetech.net/index.php/Z80:Math_Routines&Speed_Optimised_HL_div_10
;Inputs:
;     HL
;Outputs:
;     HL is the quotient
;     A is the remainder
;     DE is not changed
;     BC is 10
div16_hlby10:
	ld      bc,&0D0A
	xor     a
	add     hl,hl
	rla
	add     hl,hl
	rla
	add     hl,hl
	rla
	add     hl,hl
	rla
	cp      c
	jr      c,$+4
	sub     c
	inc     l
	djnz    $-7
	ret
; HL = starts with the number to convert to string
; DE = memory address to convertion buffer
; HL ends storing the memory address to the buffer
; subroutine taken from https://wikiti.brandonw.net/index.php?title=Z80_Routines:Other:DispA
strlib_int2str:
	ld      de,__strlib_int2str_conv
	; Detect sign of HL
	bit     7, h
	jr      z, __strlib_int2str_convert0
	; HL is negative so add '-' to string and negate HL
	ld      a,"-"
	ld      (de), a
	inc     de
	; Negate HL (using two's complement)
	xor     a
	sub     l
	ld      l, a
	ld      a, 0   ; Note that XOR A or SUB A would disturb CF
	sbc     a, h
	ld      h, a
__strlib_int2str_convert0:
	; Convert HL to digit characters
	ld      b,0    ; B will count character length of number
__strlib_int2str_convert1:
	push    bc
	call    div16_hlby10 ; HL = HL / A, A = remainder
	pop     bc
	push    af     ; Store digit in stack
	inc     b
	ld      a,h
	or      l      ; End of string?
	jr      nz, __strlib_int2str_convert1
__strlib_int2str_convert2:
	; Retrieve digits from stack
	pop     af
	or      &30    ; '0' + A
	ld      (de), a
	inc     de
	djnz    __strlib_int2str_convert2
	; Terminate string with NULL
	xor     a      ; clear flags
	ld      (de), a
	ld      hl,__strlib_int2str_conv
	ret
; HL = address to the string to print
strlib_print_str:
	ld      a,(hl)
	or      a
	ret     z
	inc     hl
	call    &BB5A
	jr      strlib_print_str


; DATA AREA

var_x: dw &00
var_tmp000: dw &00
var_tmp003: db " ",&00
var_tmp004: defs 256
var_tmp005: db " ",&00
__strlib_int2str_conv: defs 7
