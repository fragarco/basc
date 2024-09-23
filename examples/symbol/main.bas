' SYMBOL Example of use with special transparency mode
' This example is based on the Fremos old webpage and
' its series of tutorials about printing sprites in BASIC
' http://fremos.cheesetea.com/2014/03/06/sprites-con-caracteres-en-basic-amstrad-cpc

SYMBOL AFTER 240
SYMBOL 240,&00,&00,&74,&7E,&6C,&70,&7C,&30
SYMBOL 241,&7E,&FD,&80,&80,&80,&80,&40,&00
SYMBOL 242,&00,&00,&08,&00,&00,&00,&00,&00
SYMBOL 243,&00,&00,&00,&00,&10,&0C,&00,&00
SYMBOL 244,&60,&F8,&FC,&FC,&FC,&FC,&FC,&FC
SYMBOL 245,&00,&00,&60,&60,&30,&30,&00,&00
SYMBOL 246,&00,&00,&00,&00,&0C,&0C,&00,&00
SYMBOL 247,&FC,&FC,&EC,&CC,&CC,&CC,&00,&00
SYMBOL 248,&00,&00,&00,&00,&00,&00,&EE,&EE

MODE 0
PRINT CHR$(22)+CHR$(1)

LOCATE 5,2:PEN 11:PRINT CHR$(240);
LOCATE 5,2:PEN 1:PRINT CHR$(241);
LOCATE 5,2:PEN 8:PRINT CHR$(242);
LOCATE 5,2:PEN 3:PRINT CHR$(243);

LOCATE 5,3:PEN 10:PRINT CHR$(244);
LOCATE 5,3:PEN 6:PRINT CHR$(245);
LOCATE 5,3:PEN 11:PRINT CHR$(246);

LOCATE 5,4:PEN 9:PRINT CHR$(247);
LOCATE 5,4:PEN 3:PRINT CHR$(248);

LABEL loop
     GOTO loop