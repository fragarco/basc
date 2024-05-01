; Hello World Test
; A modified version from http://www.chibiakumas.com/z80/helloworld.php

org &1200
print_char equ &BB5A

main:
    ld hl, message
    call print_string
    call new_line
loop:
    jp loop

message: db "Hello world!", 255

new_line:
    ld a, 13
    call print_char
    ld a, 10
    jp print_char
    ret
    
print_string:
    ld a, (hl)
    cp 255
    ret z
    inc hl
    call print_char
    jr print_string
