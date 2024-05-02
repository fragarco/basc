; Hello World Test
; A modified version from http://www.chibiakumas.com/z80/helloworld.php
; used with the aim of testing asm.py

org &1200

main:
    ld hl, message
    call print_string
    call new_line
loop:
    jp loop

message: db "Hello World!"

read "print.asm"

