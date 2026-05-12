org 100h

.data
    infile db 'input.txt',0
    outfile db 'output.txt',0

    buffer db 5 dup(?)   ; to read "65 2"
    age db ?
    cond db ?
    result db ?

.code
start:

    ; OPEN INPUT FILE
    mov ah, 3Dh
    mov al, 0
    lea dx, infile
    int 21h
    mov bx, ax

    ; READ FULL INPUT (like "65 2")
    mov ah, 3Fh
    lea dx, buffer
    mov cx, 5
    int 21h

    ; CLOSE INPUT
    mov ah, 3Eh
    int 21h

    ; -------- PARSE AGE (2 digits) --------
    mov al, buffer[0]
    sub al, '0'
    mov bl, 10
    mul bl          ; AL = first_digit * 10

    mov dl, buffer[1]
    sub dl, '0'
    add al, dl      ; AL = full age

    mov age, al

    ; -------- PARSE CONDITION --------
    mov al, buffer[3]
    sub al, '0'
    mov cond, al

    ; -------- LOGIC --------
    mov al, age
    cmp al, 70
    ja critical

    mov al, cond
    cmp al, 3       ; ICU
    je critical

    cmp al, 1       ; heart
    je moderate
    cmp al, 2       ; cancer
    je moderate

    jmp normal

critical:
    mov result, '1'
    jmp writefile

moderate:
    mov result, '2'
    jmp writefile

normal:
    mov result, '3'

writefile:
    ; CREATE OUTPUT FILE (important fix)
    mov ah, 3Ch
    mov cx, 0
    lea dx, outfile
    int 21h
    mov bx, ax

    ; WRITE RESULT
    mov ah, 40h
    lea dx, result
    mov cx, 1
    int 21h

    ; CLOSE FILE
    mov ah, 3Eh
    int 21h

    mov ah, 4Ch
    int 21h