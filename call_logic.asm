
; You may customize this and other start-up templates; 
; The location of this template is c:\emu8086\inc\0_com_template.txt

org 100h

org 100h

.model small
.stack 100h

.data
    infile db 'input.txt',0
    outfile db 'output.txt',0

    buffer db ?
    result db ?

.code
main proc
    mov ax, @data
    mov ds, ax

    ; -----------------------------
    ; OPEN INPUT FILE
    ; -----------------------------
    mov ah, 3Dh
    mov al, 0
    lea dx, infile
    int 21h
    jc error
    mov bx, ax

    ; -----------------------------
    ; READ 1 CHARACTER
    ; -----------------------------
    mov ah, 3Fh
    lea dx, buffer
    mov cx, 1
    int 21h

    ; -----------------------------
    ; CLOSE INPUT FILE  ? FIX
    ; -----------------------------
    mov ah, 3Eh
    int 21h

    ; -----------------------------
    ; CONVERT ASCII ? NUMBER
    ; -----------------------------
    mov al, buffer
    sub al, '0'

    ; -----------------------------
    ; LOGIC
    ; -----------------------------
    cmp al, 0
    je connected

    cmp al, 2
    jle late

    cmp al, 5
    jle noanswer

    jmp switched

connected:
    mov result, '1'
    jmp writefile

late:
    mov result, '2'
    jmp writefile

noanswer:
    mov result, '3'
    jmp writefile

switched:
    mov result, '4'

writefile:
    ; -----------------------------
    ; CREATE OUTPUT FILE
    ; -----------------------------
    mov ah, 3Ch
    mov cx, 0
    lea dx, outfile
    int 21h
    jc error
    mov bx, ax

    ; -----------------------------
    ; WRITE RESULT
    ; -----------------------------
    mov ah, 40h
    lea dx, result
    mov cx, 1
    int 21h

    ; -----------------------------
    ; CLOSE OUTPUT FILE  ? FIX
    ; -----------------------------
    mov ah, 3Eh
    int 21h

    jmp exit

error:
    ; optional error handler (safe fallback)
    mov ah, 4Ch
    int 21h

exit:
    mov ah, 4Ch
    int 21h

main endp
end main

ret




