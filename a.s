.text
.global _start

_start:
    LDR SP, =0x20000
    BL F_MAIN
    MOV R0, R6
    SWI 0

F_MAIN:
    PUSH {LR}
    MOV R4, SP
    MOV R6, #71
    PUSH {R6}
    POP {R6}
    MOV SP, R4
    POP {PC}
