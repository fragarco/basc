print_char equ &BB5A

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
