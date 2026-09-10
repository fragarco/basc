<!-- omit in toc -->
ABASM: MANUAL DEL USUARIO
=========================
**Un ensamblador en Python para los Amstrad CPC**

- [Introducción](#introducción)
  - [¿Por qué otro ensamblador para Amstrad?](#por-qué-otro-ensamblador-para-amstrad)
- [Cómo se usa](#cómo-se-usa)
  - [Opciones disponibles](#opciones-disponibles)
  - [Ejemplos de uso](#ejemplos-de-uso)
  - [Creación de un proyecto usando ASMPRJ](#creación-de-un-proyecto-usando-asmprj)
- [Productos del ensamblado](#productos-del-ensamblado)
  - [El archivo binario](#el-archivo-binario)
  - [Listado del programa](#listado-del-programa)
  - [Archivo de símbolos](#archivo-de-símbolos)
- [Sintaxis](#sintaxis)
  - [Comentarios](#comentarios)
  - [Etiquetas](#etiquetas)
  - [Instrucciones](#instrucciones)
  - [Bibliotecas](#bibliotecas)
  - [Directivas del Ensamblador](#directivas-del-ensamblador)
    - [ALIGN](#align)
    - [ASSERT](#assert)
    - [DB, DM, DEFB, DEFM](#db-dm-defb-defm)
    - [DS, DEFS, RMEM](#ds-defs-rmem)
    - [DW, DEFW](#dw-defw)
    - [EQU](#equ)
    - [IF](#if)
    - [IFNOT](#ifnot)
    - [INCBIN](#incbin)
    - [MACRO](#macro)
    - [LET](#let)
    - [LIMIT](#limit)
    - [READ](#read)
    - [REPEAT](#repeat)
    - [ORG](#org)
    - [PRINT](#print)
    - [SAVE](#save)
    - [STOP](#stop)
    - [WHILE](#while)
  - [Expresiones y Caracteres Especiales](#expresiones-y-caracteres-especiales)
- [Bibliotecas incluidas en ABASM](#bibliotecas-incluidas-en-abasm)
  - [CPCRSLIB](#cpcrslib)
  - [CPCTELERA](#cpctelera)
- [Conjunto de instrucciones del Z80](#conjunto-de-instrucciones-del-z80)
- [Historial de cambios](#historial-de-cambios)

# Introducción

ABASM es un ensamblador cruzado diseñado específicamente para la plataforma Amstrad CPC y su CPU Z80. Desarrollado en Python 3, su principal objetivo es proporcionar una herramienta ligera y altamente portable para programadores interesados en crear código ensamblador para esta clásica plataforma de 8 bits. Al no depender de librerías externas ni herramientas de terceros, ABASM puede ejecutarse en cualquier sistema que cuente con un intérprete de Python 3. Además, el proyecto incluye otras herramientas, también programadas en Python y sin dependencias, por ejemplo, para empaquetar el resultado del ensamblador en archivos DSK o CDT incluye DSK.py y CDT.py. Para la creación de una estructura básica de proyecto, incluye la herramienta ASMPRJ.py.

ABASM está basado en el fantástico proyecto pyZ80, creado inicialmente por Andrew Collier y modificado posteriormente por Simon Owen.

## ¿Por qué otro ensamblador para Amstrad?

ABASM surge de la idea de contar con una herramienta portable y fácil de modificar por cualquiera, sin depender de sistemas operativos específicos o entornos de desarrollo particulares. Uno de sus objetivos es proporcionar una sintaxis compatible con el antiguo ensamblador MAXAM, con la sintaxis de WinAPE y con la de Virtual Machine Simulator. De esta forma, los desarrolladores pueden contar con varias opciones para depurar su código durante el desarrollo.

En cualquier caso, si lo que buscas es eficiencia en vez de portabilidad y facilidad de modificación, quizás quieras probar estos otros ensambladores:

* [Pasmo](https://pasmo.speccy.org/)
* [ASZ80](https://shop-pdp.net/ashtml/)
* [Rasm](https://github.com/EdouardBERGE/rasm)

# Cómo se usa

Para ensamblar un archivo fuente de código en ensamblador (por ejemplo, `program.asm`), basta con ejecutar el siguiente comando:

```
python3 ABASM.py <program.asm> [opciones]
```

Este comando ensamblará el archivo `program.asm` y generará un fichero binario con el mismo nombre, `program.bin`.

## Opciones disponibles

- `-d` o `--define`: Permite definir pares `SÍMBOLO=VALOR`. Dichos símbolos pueden utilizarse en el código como constantes o etiquetas. Esta opción se puede emplear múltiples veces para definir varios símbolos.
- `--start`: Define la dirección de memoria que se tomará como punto de inicio para la carga del programa. Por defecto, esta dirección es `0x4000`, aunque también puede establecerse directamente dentro del código usando la directiva `ORG`.
- `-t` o `--tolerance`: Fija el nivel de tolerancia ante alternativas a los opcodes soportados y ante otros pequeños errores. WinApe es bastante laxo en la comprobación de la sintaxis, así que puede ser necesario utilizar esta opción si se está trabajando con código proveniente de este programa. Por defecto, su valor es 0, el modo más estricto y menos permisivo. Los valores 1 y 2 incrementan progresivamente el nivel de tolerancia.
- `s` o `--sfile`: Genera un único fichero .s con todo el código ensablado, incluyendo el código importado de otros ficheros.
- `-o` o `--output`: Especifica el nombre del archivo binario de salida. Si no se utiliza esta opción, se empleará el nombre del archivo de entrada cambiando su extensión por `.bin`.
- `-v` o `--version`: Muestra el número de versión de ABASM.
- `--verbose`: Imprime mucha más información por consola durante el proceso de ensamblado. 

## Ejemplos de uso

Definir una constante utilizada en el código:

```
python3 ABASM.py program.asm -d MY_CONSTANT=100
```

Establecer el nombre exacto del archivo binario ensamblado:

```
python3 ABASM.py program.asm -o output.bin
```

Establecer la dirección de inicio en memoria que debe considerarse para el cálculo de los saltos y otras referencias relativas utilizadas en el código fuente, por ejemplo, a `0x2000`:

```
python3 ABASM.py program.asm --start 0x2000
```

## Creación de un proyecto usando ASMPRJ

En `ABASM`, la gestión de un proyecto es sencilla. Basta con crear un fichero principal en ensamblador que importe cualquier otro archivo necesario mediante la directiva `READ`. Tras ejecutar `ABASM`, se generará el fichero binario ensamblado. A continuación, solo será necesaria una llamada adicional a las herramientas `DSK` o `CDT` para empaquetar el resultado y poder utilizarlo en emuladores o en hardware real (por ejemplo, mediante dispositivos como Gotek, M4 o DDI-Revival).

```bash
python3 abasm.py main.asm
python3 dsk.py -n main.dsk --put-bin main.bin --start-addr=0x4000 --load-addr=0x4000
```

Además, es posible generar rápidamente la estructura básica de un proyecto utilizando la herramienta `ASMPRJ`. Esta utilidad crea automáticamente un script de construcción con todo lo necesario para comenzar a trabajar: en Windows se generará un fichero `make.bat`, mientras que en Linux y macOS se creará un fichero `make.sh`. Asimismo, se incluirá un archivo `main.asm` con código de ejemplo listo para ser ensamblado y probado.

```bash
python3 asmprj.py -n myproject
```

Para conocer todas las opciones disponibles, se recomienda consultar la documentación específica de `ASMPRJ`.

# Productos del ensamblado

Una ejecución exitosa de ABASM genera varios archivos. En esta sección se proporciona una breve explicación de cada uno de dichos productos.

## El archivo binario

El resultado final del proceso de ensamblado es un archivo binario (normalmente con la extensión `.BIN`) listo para su carga en memoria y ejecución en un Amstrad CPC. El código fuente puede dividirse en varios archivos, pero solo uno, el principal, se pasa como parámetro a ABASM para iniciar el ensamblado. El resto de archivos se añadirán a medida que se referencien mediante las directivas `READ` o `INCBIN`.

ABASM no genera código relocalizable, lo que significa que asume una dirección inicial de carga en memoria. Esta dirección de carga puede indicarse como un parámetro en la llamada a ABASM o puede establecerse en el propio archivo principal mediante la directiva `ORG`.

Por ejemplo, el siguiente código en ensamblador, que carga el valor `0xFF` en la primera posición de la memoria de vídeo, generaría el contenido binario que se muestra a continuación (como una secuencia de valores en hexadecimal).

```
org  0x4000       ; Fijamos la dirección inicial de carga en memoria

main:
    ld   a,0xFF       ; Cargamos en el acumulador el valor 0xFF
    ld   (0xC000),a   ; Cargamos en el primer byte de la memoria 
                      ; de vídeo el contenido de A
endloop:              ; Bucle infinito
    jp endloop        ; El valor de 'endloop' se calculará 
                      ; según el valor inicial indicado por ORG
```

```
3E FF 32 00 C0 C3 05 40
```

Dado que el Z80 es *little-endian*, podemos ver que los últimos tres bytes son `C3 05 40`, lo que equivale a `C3 4005`, que es el resultado en código máquina para `jp endloop`, con `endloop` calculado a partir de la dirección de inicio `0x4000`.

## Listado del programa

Como referencia para el programador, el proceso de ensamblado también genera un archivo con el listado del programa original y el resultado binario de cada una de las instrucciones. La extensión de este archivo es `.LST`.

Siguiendo con el ejemplo proporcionado anteriormente, el archivo `.LST` generado tendría el siguiente contenido:

```
main.asm      000001  4000               	org  0x4000
main.asm      000002  4000               	main
main.asm      000003  4000  3E FF        	ld   a, 0xFF
main.asm      000004  4002  32 00 C0     	ld  (0xC000), a
main.asm      000005  4005               	endloop
main.asm      000006  4005  C3 05 40     	jp endloop
```

El nombre del archivo origen aparece en la primera columna, mientras que la segunda indica el número secuencial de la instrucción en dicho archivo. La tercera columna indica qué posición de memoria ocupar el código generado (si se ha generado alguno, ya que algunas directivas y etiquetas no generan código binario). La cuarta columna muestra el código binario resultante de ensamblar la instrucción y la última columna la instrucción original.

## Archivo de símbolos

ABASM también genera un listado de todos los símbolos globales encontrados y su valor asociado. La mayoría de ellos serán etiquetas utilizadas para marcar posiciones de salto o ubicaciones de memoria donde se han almacenado ciertos datos. Los símbolos locales son aquellos que comienzan con el caracter '!'.

La extensión del fichero de símbolos es `.MAP` y su formato es el de un diccionario de Python. Esto permite emplear el archivo en otras utilidades (como los empaquetadores DSK y CDT) y utilizar los símbolos en lugar de sus valores. En la documentación sobre las utilidades DSK y CDT se puede encontrar un ejemplo de uso de este archivo.

```
# Lista de símbolos en formato de diccionario de Python
# Símbolo: [dirección, número total de consultas (usos), nombre del archivo]
{
	"ENDLOOP": [0x4005, 2, "MAIN.ASM"],
	"MAIN": [0x4000, 1, "MAIN.ASM"],
}
```

# Sintaxis

La sintaxis de ABASM está diseñada para asemejarse lo máximo posible a la del ensamblador MAXAM. Esta sintaxis es bastante compatible con la soportada por el simulador WinAPE. Además, ABASM admite algunas variaciones que también lo hacen compatible con la sintaxis utilizada por el simulador Retro Virtual Machine. El objetivo es permitir que los desarrolladores cuenten con varias herramientas para la depuración y prueba de sus programas.

A continuación, se muestra un ejemplo sencillo de un programa escrito utilizando la sintaxis de ABASM. Este ejemplo muestra tres de los elementos básicos de cualquier programa escrito en ensamblador: etiquetas, instrucciones y comentarios. Un cuarto elemento serían las directivas del ensamblador, comandos dirigidos al propio ABASM en lugar de al procesador. En este capítulo también repasaremos el listado completo de las directivas soportadas.

Un aspecto importante y común a los cuatro elementos es que ABASM no discrimina entre mayúsculas y minúsculas. Por lo tanto, 'LD A,32' y 'ld a,32' producen el mismo resultado. Lo mismo se aplica a las etiquetas: 'main', 'MAIN' o 'Main' se consideran la misma etiqueta.

```
; Imprime todos los caracteres ASCII entre el código 32 y 128.
; Es una variación del primer ejemplo presentado en el
; manual de MAXAM

main              ; define la etiqueta global 'main'
    ld a,32       ; primer código de letra ASCII en el acumulador

!loop             ; define la etiqueta local 'loop'
    call &BB5A    ; LLAMA a txt_output, la rutina de salida del firmware
    inc  a        ; pasa al siguiente carácter
    cp   128      ; ¿hemos terminado con todos?
    jr   c,!loop  ; no - regresa para procesar el siguiente

.end  
    jp   end      ; bucle infinito usado como punto final del programa

```

Otro aspecto importante de ABASM es que permite usar el símbolo '!' al principio de las etiquetas para definir las que son locales y solo accesibles desde el archivo o módulo en el que son declaradas.

## Comentarios

Los comentarios en código ensamblador son anotaciones escritas por el programador que no serán interpretadas ni ejecutadas por la CPU. Su objetivo es proporcionar información adicional sobre el código para hacerlo más comprensible y mantenible.

Los comentarios son importantes en cualquier lenguaje de programación, pero en ensamblador adquieren una relevancia aún mayor, ya que debido al bajo nivel de abstracción del lenguaje, el código no suele ser fácil de interpretar. Por lo tanto, son cruciales para explicar su propósito y funcionamiento. Como norma general, se recomienda hacer uso de los comentarios para:

- Describir partes complejas del código, explicando qué hace una secuencia particular de instrucciones o los parámetros y valores que devuelve una subrutina.
- Delimitar secciones del código, como bucles, funciones o bloques lógicos.
- Proporcionar contexto, indicando el propósito de una variable, etiqueta o constante.

En ABASM, los comentarios suelen indicarse con el carácter ';' (punto y coma). Cuando ABASM encuentra este carácter, procede a ignorar el resto de la línea.

```
; Esto es un comentario
; Esto es otro comentario
```

## Etiquetas

Las etiquetas en el código ensamblador son nombres simbólicos utilizados para marcar una posición específica en el programa, como una dirección de memoria o una instrucción. Sus principales usos son:

- En saltos y bucles: Las etiquetas se usan como destinos en instrucciones de salto (JMP, JE, etc.), permitiendo redirigir el flujo de ejecución a una parte específica del programa.

- En la definición de datos: Se utilizan para referirse a variables o datos en memoria, facilitando su acceso y manipulación.

- Como puntos de entrada a bloques de código: Ayudan a hacer el código más legible y fácil de mantener al proporcionar nombres descriptivos a secciones importantes del programa.

Todas las etiquetas son **globales** por defecto, lo que significa que deben ser únicas sin importar en cuántos archivos esté dividido el código fuente. ABASM ignora el carácter inicial '.' en la definición de etiquetas para admitir el formato de declaración de etiquetas de WinApe.  

Para crear una etiqueta local (restringida a un módulo/archivo o dentro de una macro), debe comenzar con el símbolo '!'. Si la etiqueta se define fuera de una macro, se considera una **etiqueta local del módulo**, accesible solo dentro del archivo donde se declara. Esto también evita que la etiqueta aparezca en el archivo de símbolos.  

Si la etiqueta se define dentro de una macro, se trata como una **etiqueta local de macro**. Las etiquetas locales de macro son esenciales para evitar errores causados por redefiniciones de etiquetas cuando la macro se invoca varias veces.  

```
!loop
  <algo de código>
  dec b
  jr z,!loop
```

## Instrucciones

Las instrucciones son operaciones que debe realizar la CPU (el procesador Z80 en nuestro caso). El proceso de ensamblar consiste en generar el código binario correspondiente a estas instrucciones. Cada instrucción suele estar compuesta por un *opcode* y sus *operandos*.

Un opcode (abreviatura de "operation code" o código de operación) es la parte de una instrucción que especifica la acción que debe realizar la CPU. Es un valor binario o hexadecimal único asociado a una operación particular, como sumar, restar, cargar un valor en un registro o realizar una comparación. Por lo tanto, el opcode determina la operación a ejecutar, mientras que los operandos (si los hay) proporcionan los datos necesarios para dicha operación. Por ejemplo:

```
ld a,32
```

El *opcode* (el nemotécnico asociado más bien) sería 'ld a', mientras que el operando sería '32'. El significado del opcode es 'cargar en el registro A', mientras que el valor a cargar sería directamente el número 32.

ABASM soporta todas las instrucciones estándar del Z80. Con la intención de mejorar la compatibilidad con la sintaxis de WinAPE, algunas instrucciones como AND, CP, OR y SUB pueden incluir el registro A como parte del *opcode*. Sin embargo, se prefiere la forma abreviada sin el A explícito. Los usuarios pueden controlar como de permisivo es el ensablador a través del parámetro `--tolerance NIVEL`. Según su valor, estas variaciones pueden considerarse un error, emitir un *warning* o ser aceptadas por completo.

| Nivel de tolerancia | Comportamiento |
| ------------- | ------------- |
| --tolerance 0 | Valor por defecto, el modo más estricto. Los opcodes SUB A, CP A, etc., tolerados por WinApe producen un error de sintaxis en ABASM. |
| --tolerance 1 | Los opcodes alternativos de WinApe SUB A, CP A, etc., producen un *warning* pero no detienen el ensamblado. |
| --tolerance 2 | Los opcodes alternativos se aceptan completamente. Los errores debidos a truncamientos, por ejemplo, valor de dos bytes utilizado en un operando de un byte, producen *warnings* en vez de errores. |

A nivel de operandos, ABASM es totalmente compatible con los registros estándar de 8 bits del Z80: A, B, C, D, E, H y L, así como con los registros especiales de 8 bits I y R. También es compatible con todos los registros estándar de 16 bits del Z80: AF, BC, DE, HL y SP, junto con los registros de índice IX e IY. Además, ABASM ofrece soporte para el uso no documentado de las porciones de 8 bits de los registros IX e IY, permitiendo el uso de IXL, IXH, IYL e IYH. El registro alternativo AF' también se puede utilizar en las instrucciones adecuadas, como con la instrucción `EX AF, AF'`.

Por último, ABASM soporta las condiciones habituales NZ, Z, NC, C, PO, PE, P y M en las instrucciones diseñadas para tal fin, como, por ejemplo, las intrucciones de salto condicional.

Para consultar los detalles específicos sobre cada instrucción, se puede recurrir a la lista incluida en la sección `Conjunto de instrucciones del Z80` o a los siguientes sitios web (en inglés):

- [@ClrHome Tabla de Instrucciones del Z80](https://clrhome.org/table/): Una tabla bien organizada que proporciona un resumen conciso de todas las instrucciones del Z80.
- [Documentación oficial de Zilog para el procesador Z80](https://www.zilog.com/docs/z80/um0080.pdf): Especialmente útiles son las dos últimas secciones tituladas *Z80 CPU Instructions* y *Z80 Instruction Set*.
- [Z80 Heaven](http://z80-heaven.wikidot.com/): Una web de referencia con información detallada de cada instrucción.

En español, se pueden consultar los siguientes enlaces:

- [Resumen sobre el procesador Z80](https://ia801404.us.archive.org/7/items/z80-cpu-manual/ES%20-%20Z80%20CPU%20Manual.pdf): Un documento de 19 páginas con un buen resumen del procesador Z80 y su juego de instrucciones.
- [Juego de instrucciones del microprocesador Z80](https://www.infor.uva.es/~bastida/OC/Tablas%20Z80%20SPARC%20y%20ASCII.pdf): Otro buen documento centrado en las instrucciones soportadas por el procesador Z80.
- [Dominando el ensamblador Z80 (DEZ80) de la Universidad de Alicante](https://www.cpcwiki.eu/index.php/DEZ80): Serie de librosCurso de programación en ensamblador para el Amstrad CPC impartido por el profesor Francisco Gallego y en formato de vídeos.

## Bibliotecas

La directiva `read` permite incluir archivos adicionales desde un archivo principal. Estos archivos pueden ser locales o residir dentro de la carpeta `lib` de la instalación. De esta manera, es posible crear bibliotecas reutilizables entre proyectos.

Como ejemplo, la distribución de **ABASM** incluye una versión reducida de la biblioteca **CPCRSLIB** y una versión completa de la biblioteca **CPCTELERA**. Para obtener más detalles, puedes consultar los ejemplos disponibles en la carpeta `examples/cpcrslib` y `examples/cpctelera`.

## Directivas del Ensamblador

Una directiva en ensamblador es una instrucción que no se traduce directamente en código máquina para la CPU, sino que proporciona información o instrucciones al ensamblador sobre cómo procesar el código fuente. Estas directivas controlan aspectos del proceso de ensamblado, como la organización del código, la definición de datos, la asignación de memoria y la definición de constantes. A diferencia de las instrucciones que se ejecutan en la CPU, las directivas solo afectan al ensamblador durante el ensamblado del código fuente. Ejemplos comunes incluyen ORG (para establecer la dirección de inicio), EQU (para definir constantes) o DB (para definir datos en memoria). A continuación, se presenta una lista completa de las directivas soportadas por ABASM y su significado:

### ALIGN

- ALIGN n [,v]

*n* debe ser un número o una expresión numérica que sea una potencia de dos. Esta directiva añade los bytes necesarios para que la memoria utilizada hasta ese momento por el programa sea un múltiplo de *n*. El segundo parámetro opcional establece el valor con el que debe rellenarse la memoria necesaria (un valor entre 0 y 255). Si no se especifica este segundo argumento, la memoria se rellena con ceros.

Por ejemplo:

```
main:
    LD A, 0xFF
    ALIGN 8
data:
    DB 0xAA, 0xBB, 0xCC
```

Esto producirá el siguiente código binario:

```
3E FF 00 00 00 00 00 00 AA BB CC
```

### ASSERT

- ASSERT condición

Esta directiva evalúa si la condición proporcionada se cumple. Si no es así, aborta el proceso de ensamblado. Por ejemplo, el siguiente código verifica que la siguiente instrucción a ensamblar no ocupe una posición de memoria superior al inicio de la memoria de video (0xC000 en el Amstrad CPC).

```
ASSERT @<0xC000
```

Los operadores básicos que se pueden usar en estar expresiones son:
 - *==* : igual que.
 - *!=* : distinto que.
 - *<*, *>* : menor que o mayor que.  
 - *<=*, *>=*: menor o igual que, mayor o igual que. 

### DB, DM, DEFB, DEFM 

- DEFB  n [,n ...]
- DEFM  n [,n ...]
- DB    n [,n ...]
- DM    n [,n ...]

Almacena en la posición actual de memoria la lista de bytes proporcionada como parámetro. *n* puede ser un número o una expresión numérica en el rango de 0 a 255 (0x00 a 0xFF).

```
DB 0xFF, 0xFF, 0xFF, 0xFF
```

También es posible usar una cadena de texto como parámetro y combinarla con el formato anterior. En este caso, se almacenarán los códigos ASCII de cada letra como si fueran los valores numéricos proporcionados.

```
DB "Hola Mundo",0x00
```

### DS, DEFS, RMEM

- DEFS  n
- DS    n
- RMEM  n

Reserva *n* bytes de memoria. Básicamente, la posición actual de memoria se incrementa en *n* bytes, dejándola libre para su uso posterior.

### DW, DEFW

- DEFW  n [,n ...]
- DW    n [,n ...]

Almacena *palabras* (dos bytes en formato little-endian) en la posición actual de memoria. *n* puede ser un número o una expresión numérica en el rango de 0 a 65535 (0x0000 a 0xFFFF).

```
year:
    DW  2024
```

### EQU

- EQU símbolo, valor
- símbolo EQU valor

Permite establecer el valor de un símbolo, normalmente utilizado como constante.

```
EQU MEM_VIDEO, 0xC000

LD  A,0xFF
LD  (MEM_VIDEO),A
```

### IF

- IF condición [ELSEIF condición | ELSE] ENDIF

La directiva IF permite que ciertas partes del código se incluyan o se ignoren, dependiendo del valor de una expresión lógica. Dicha expresión puede contener símbolos y valores numéricos. Si la expresión es verdadera (distinta de cero), el ensamblador procesará las líneas que siguen a la directiva IF. Si es falsa (igual a cero), esas líneas serán ignoradas.

Una estructura básica de IF podría ser:

```
IF expresión
    ; Código ensamblado si la expresión es verdadera
ELSE
    ; Código ensamblado si la expresión es falsa
ENDIF
```

Esta directiva es útil cuando se combina con la opción `--define` de ABASM, que permite cambiar qué código se ensambla dependiendo de la llamada hecha al ensamblador. Sin embargo, cualquier símbolo o constante referenciada en la expresión lógica debe haberse declarado previamente.

Los operadores básicos que se pueden usar en estar expresiones son:
 - *=* : aunque == es el operador adecuado, ABASM soporta '=' por compatibilidad con WinAPE.
 - *==* : igual que.
 - *!=* : distinto que.
 - *<*, *>* : menor que o mayor que.  
 - *<=*, *>=*: menor o igual que, mayor o igual que.  


### IFNOT

- IFNOT condición [ELSEIF condición | ELSE] ENDIF

La directiva IFNOT permite que ciertas partes del código se incluyan o se ignoren, dependiendo del valor de una expresión lógica, de igual forma a como se comporta la directiva `IF`. Sin embargo, el ensamblador procesará las líneas que siguen a la directiva IFNOT solo cuando dicha expresión sea falsa (igual a cero).

### INCBIN

- INCBIN "fichero binario"

Esta directiva inserta el contenido del fichero especificado entre comillas dobles. La ruta del fichero debe ser relativa a la ubicación del fichero que lo incluye.

```
INCBIN "./assets/mysprite.bin"
```

### MACRO

- MACRO símbolo [param1, param2, ...] ENDM

Esta directiva permite asignar un nombre o símbolo a un bloque de código que se extiende hasta la siguiente ocurrencia de ENDM. La macro puede incluir una lista de parámetros que serán sustituidos por los valores proporcionados en futuras *llamadas* a la macro. Una vez definida, una macro puede utilizarse en el resto del código como si fuera una instrucción convencional. Los parámetros se buscan en el código de la macro y se sustituyen por los valores pasados en la *llamada*. Por ese motivo, puede ser una buena práctica comenzar y finalizar cada nombre de parámetro con el carácter '_'; evitando, de ese modo, coincidencias accidentales con otras cadenas de texto o con nombres de registros o directivas.

```
macro get_screenPtr _REG_, _X_, _Y_ 
   ld _REG_, &C000 + 80 * (_Y_ / 8) + 2048 * (_Y_ & 7) + _X_ 
endm

main:
   get_screenPtr hl, 20, 10
``` 

El código de una macro puede contener *llamadas* a otras macros, pero no es posible definir una nueva macro ni utilizar la directiva **READ**. Si una macro contiene una etiqueta normal (global o local al módulo) y se *llama* más de una vez, el ensamblador detectará una redefinición de la etiqueta, lo que provocará un error. Si una macro necesita emplear etiquetas en su código, estas deben ir precedidas del símbolo '!', lo que las identificará como **etiquetas locales a la macro**.

```
macro decnz_a
  or a
  jr z,!leave
  dec a
  !leave
mend
```

WinApe utiliza el símbolo '@' para identificar **etiquetas de macro locales**, pero ese símbolo lo utiliza ABASM como la dirección actual en memoria para el código ensamblado. Por tanto, ABASM no es compatible con WinApe en este aspecto.

Si una misma macro se define una segunda vez, la segunda definición pasa a ser la valida desde ese momento. Sin embargo, también es posible emplear la directiva `MDELETE símbolo` para eliminar una definición existente.

### LET

- LET símbolo=valor

Esta directiva permite cambiar el valor de un símbolo o constante. Este símbolo o constante debe haber sido definido inicialmente con LET.

```
LET PADDING=0x00
<código>
LET PADDING=0xFF
<más código>
```

### LIMIT

- LIMIT dirección_de_memoria

Establece la dirección máxima de memoria que puede alcanzar el programa ensamblado. El valor suministrado puede ser un número o una expresión numérica. Por defecto, este valor es 65536 (64K).

```
LIMIT &C000   ; protegemos la memoria de video que empieza en &C000
ORG &C000
LD A,&FF      ; esta linea causará un error
```

### READ

- READ "fichero de código fuente"

Esta directiva inserta el contenido del fichero especificado entre comillas dobles o siemples y lo ensambla. La ruta del fichero debe ser relativa a la ubicación del fichero que lo incluye. Todos los símbolos definidos en el fichero insertado son globales, por lo que deben ser únicos y no repetirse en el fichero principal ni en ningún otro fichero incluido mediante este método. Si un mismo fichero se incluye varias veces, ABASM lo detectará y solo lo incluirá una vez.

```
READ "./lib/keyboard.asm"
```

### REPEAT

- REPEAT expresión numérica `bloque de código` REND

Repite un bloque de código tantas veces como el valor indicado por la expresión numérica. No puede utilizarse dentro de la definición de una macro.

```
EQU ENTITIES, 10
LET ENTITY_ID = 0
REPEAT ENTITIES
  DB 0x00       ; X pos
  DB 0x00       ; Y pos
  DB ENTITY_ID  ; Entity ID
  LET ENTITY_ID = ENTITY_ID + 1
REND
```

### ORG

- ORG dirección_de_memoria

Especifica la dirección de memoria que debe considerarse como la actual a partir de ese momento para cualquier cálculo necesario, como establecer el valor de una etiqueta. Lo habitual es que esta directiva aparezca como la primera instrucción del código fuente, aunque puede substituirse por la opción de ABASM `--start`.

```
ORG 0x4000
```

Nada impide incluir más de una ocurrencia de esta directiva en el código fuente, aunque hay que tener presente que cualquier zona de memoria "vacia" que quede entre la dirección de memoria inicial del programa y la dirección más alta será rellenada con 0s, aumentando el tamaño del fichero `bin` resultante. Para evitarlo, si un programa necesita tener partes cargadas en diferentes áreas de la memoria, es aconsejable generar un fichero binario independiente para cada área y empaquetarlos todos dentro del mismo DSK o CDT, junto con un cargador programado en BASIC (por ejemplo).

### PRINT

- PRINT expresión[, expresión ...]

Imprime el resultado de la(s) expresión(es) proporcionada(s) en la salida estándar tan pronto como se evalúe durante el ensamblado. Esto puede ser útil para generar información adicional durante el ensamblado, como la memoria total que consume el programa.

```
ORG 0x4000
<código>
PRINT @-0x4000
```
### SAVE

- SAVE "fichero", expresión numérica, expresion numérica

Esta directiva permite generar archivos binarios adicionales con el contenido de la memoria en la que se está escribiendo el código ensamblado. La memoria tiene un tamaño máximo de 64K, que corresponde al límite del Amstrad CPC 464. La primera expresión define la dirección de inicio, mientras que la segunda especifica la cantidad total de bytes que se escribirán en el archivo.

```
SAVE "myscreen.bin",&C000,&4000
```

### STOP

- STOP

Detiene inmediatamente el proceso de ensamblado mostrando un error.

### WHILE

- WHILE expresión lógica `bloque de código` WEND

Permite ensamblar repetidamente un bloque de código mientras se cumpla la condición especificada. Si la condición nunca llega a ser falsa, esta directiva puede generar un bucle infinito. No puede utilizarse dentro de la definición de una macro.

```
LET OBJECTS = 32
WHILE OBJECTS>0
  db 0
  db 0
  db 0
  LET OBJECTS = OBJECTS-1
WEND
```

## Expresiones y Caracteres Especiales

Cuando una instrucción o directiva requiere un número como parámetro, se puede usar una expresión matemática en su lugar. Estas expresiones pueden hacer referencia a cualquier símbolo definido en el código. Si el resultado de una expresión es negativo, se utiliza su complemento a dos como valor. Además, algunos símbolos tienen significados especiales, que se detallan a continuación:

- **$** representa la dirección de memoria de la instrucción actual.
- **@** es intercambiable con el símbolo **$**.
- El prefijo **&** indica números en formato hexadecimal (por ejemplo, &FF).
- El prefijo **#** indica números en formato hexadecimal (por ejemplo, #FF).
- El prefijo **0x** también indica números en formato hexadecimal (por ejemplo, 0xFF).
- El prefijo **%** indica números en formato binario (por ejemplo, %11111111).
- El prefijo **0b** también indica números en formato binario (por ejemplo, 0b11111111).
- Las comillas dobles **"** delimitan caracteres o cadenas de texto (1).
- Las comillas simples **'** son equivalentes a las dobles para delimitar cadenas de texto.
- **MOD** es el operador módulo: op1 MOD op2.
- **AND** es el operador bit a bit AND: op1 AND op2. También se puede usar el operador & de Python.
- **OR** es el operador bit a bit OR: op1 OR op2. También se puede usar el operador | de Python.
- **XOR** es el operador bit a bit XOR: op1 XOR op2. También se puede usar el operador ^ de Python.
- **<<** es el operador *desplazamiento* a la izquierda.
- **>>** es el operador *desplazamiento* a la derecha.
  
(1) Un único carácter entre comillas dobles puede usarse para representar el valor ASCII de ese carácter en expresiones numéricas. Ni las comillas dobles ni las simples pueden aparecer dentro de una cadena de texto.

# Bibliotecas incluidas en ABASM

`ABASM` incluye dos bibliotecas listas para uso.. Ambas con un gran recurso para aprender más sobre los entresijos del Amstrad CPC, incluyendo su preculiar organización de la memoria de vídeo.

## CPCRSLIB

CPCRSlib es una biblioteca en C que proporciona rutinas y funciones para la gestión de sprites y mapas de tiles en el Amstrad CPC. La biblioteca está diseñada para su uso con los compiladores Z88DK o SDCC. CPCRSlib también incluye rutinas de teclado para la redefinición y detección de teclas, así como rutinas de propósito general para cambiar el modo de pantalla y los colores.

Además, CPCRSLIB incorpora un reproductor de música y efectos de sonido desarrollado por WYZ, capaz de reproducir música creada con WYZTracker.

* Una explicación detallada de cada función y rutina se puede consultar aquí:
  [http://www.amstrad.es/programacion/cpcrslib.html](http://www.amstrad.es/programacion/cpcrslib.html)
* La última versión oficial de la biblioteca original puede descargarse desde:
  [http://sourceforge/cpcrslib](http://sourceforge/cpcrslib)

La versión incluida con `ABASM` no incorpora soporte para el desplazamiento de tilemaps. Adicionalmente, algunas rutinas han sido renombradas para mejorar la claridad y la coherencia. Consulta los ejemplos ubicados en `examples/cpcrslib` para aprender más sobre el uso de esta biblioteca dentro de `ABASM`.

## CPCTELERA

CPCtelera es un framework multiplataforma para el desarrollo de videojuegos y software multimedia para el Amstrad CPC. Funciona en Linux, macOS y Windows (mediante Cygwin) y facilita el desarrollo de software para Amstrad CPC tanto en lenguaje C como en ensamblador. CPCtelera requiere el uso del compilador SDCC y el ensamblador que incluye.

CPCtelera está ampliamente documentada, dispone de un completo manual de referencia y su código fuente está profusamente comentado. Todos los detalles y la documentación pueden consultarse en:

* [https://lronaldo.github.io/cpctelera/](https://lronaldo.github.io/cpctelera/)
* [https://lronaldo.github.io/cpctelera/files/readme-txt.html](https://lronaldo.github.io/cpctelera/files/readme-txt.html)

El port incluido en `ABASM` cubre todas las rutinas disponibles en la versión 1.5-dev de CPCtelera. La principal diferencia es que el sufijo `_asm` ha sido eliminado de los nombres de las rutinas, ya que en este contexto no existe ambigüedad entre código C y ensamblador. Para aprender más sobre el uso de esta biblioteca dentro de `ABASM` pueden consultarse los ejemplos incluidos en `examples/cpctelera`.

# Conjunto de instrucciones del Z80

Esta sección proporciona una lista breve de todas las instrucciones soportadas del Z80. Lo habitual en muchos otros lugares es indicar los tiempos de ejecución en ciclos o *T-states*. Sin embargo, el Amstrad CPC tiene su propia temporización debido a que el Gate Array pausa el Z80 para acceder a la memoria de video. Por lo tanto, es más preciso medir los tiempos de ejecución en función del coste de la instrucción NOP (1 microsegundo). Los tiempos de cada instrucción también se pueden consultar en la siguiente página web:

- [Tiempos del Z80 para el Amstrad CPC - Hoja de referencia rápida](https://www.cpcwiki.eu/imgs/b/b4/Z80_CPC_Timings_cheat_sheet.20230709.pdf)

**Claves:**
```
r 	  registro de 8 bits (B,C,D,E,H,L,A)
n     valor numérico de 8 bits (rango 0-254)
hh 	  valor hexadecimal de 8 bits (rango &00-&FF)
d 	  offset numérico de 1 byte (-128 a 127)

rr 	  registro doble de 16 bits (HL,DE,BC)
nn    valor numérico de 16 bits (rango 0-65535)
HHhh 	valor hexadecimal de 16 bits (rango &0000-&FFFF)

cc	  condición (z,nz,c,nc,p,m,po,pe)
cn 	  condición no satisfecha
cs 	  condición satisfecha

b     posición de un bit dentro de un byte (7-0)
```

**Lista de instrucciones:**
```
bytes         opcode        tiempo    explicación
-------------------------------------------------------------------------------
8F          	ADC   A,A       1 Suma con acarreo el registro r al acumulador.
88          	ADC   A,B
89          	ADC   A,C
8A          	ADC   A,D
8B          	ADC   A,E
8C          	ADC   A,H
8D          	ADC   A,L
CE hh       	ADC   A,n       2 Suma con acarreo el valor n al acumulador.
DD 8C       	ADC   A,IXH     2 Suma con acarreo el byte alto de IX al acumulador.
DD 8D       	ADC   A,IXL     2 Suma con acarreo el byte bajo de IX al acumulador.
FD 8C       	ADC   A,IYH     2 Suma con acarreo el byte alto de IY al acumulador.
FD 8D       	ADC   A,IYL     2 Suma con acarreo el byte bajo de IY al acumulador.
8E          	ADC   A,(HL)    2 Suma con acarreo el valor en la ubicación HL al acumulador.
DD 8E hh    	ADC   A,(IX+d)  5 Suma con acarreo el valor en la ubicación IX+d al acumulador.
FD 8E hh    	ADC   A,(IY+d)  5 Suma con acarreo el valor en la ubicación IY+d al acumulador.
ED 4A       	ADC   HL,BC     4 Suma con acarreo el registro doble rr a HL.
ED 5A       	ADC   HL,DE
ED 6A       	ADC   HL,HL
ED 7A       	ADC   HL,SP

87          	ADD   A,A       1 Suma el registro r al acumulador.
80          	ADD   A,B
81          	ADD   A,C
82          	ADD   A,D
83          	ADD   A,E
84          	ADD   A,H
85          	ADD   A,L
C6 hh       	ADD   A,n       2 Suma el valor n al acumulador.
DD 84       	ADD   A,IXH     2 Suma el byte alto de IX al acumulador.
DD 85       	ADD   A,IXL     2 Suma el byte bajo de IX al acumulador.
FD 84       	ADD   A,IYH     2 Suma el byte alto de IY al acumulador.
FD 85       	ADD   A,IYL     2 Suma el byte bajo de IY al acumulador.
86          	ADD   A,(HL)    2 Suma el valor en la ubicación HL al acumulador.
DD 86 hh    	ADD   A,(IX+d)  5 Suma el valor en la ubicación IX+d al acumulador.
FD 86 hh    	ADD   A,(IY+d)  5 Suma el valor en la ubicación IY+d al acumulador.
09          	ADD   HL,BC     3 Suma el registro doble rr a HL.
19          	ADD   HL,DE
29          	ADD   HL,HL
39          	ADD   HL,SP
DD 09       	ADD   IX,BC     4 Suma el registro doble rr a IX.
DD 19       	ADD   IX,DE
DD 29       	ADD   IX,IX
DD 39       	ADD   IX,SP
FD 09       	ADD   IY,BC     4 Suma el registro doble rr a IY.
FD 19       	ADD   IY,DE
FD 29       	ADD   IY,IY
FD 39       	ADD   IY,SP

A7          	AND   A         1 AND lógico del registro r con el acumulador.
A0          	AND   B
A1          	AND   C
A2          	AND   D
A3          	AND   E
A4          	AND   H
A5          	AND   L
E6 hh       	AND   n         2 AND lógico del valor n con el acumulador.
DD A4       	AND   IXH       2 AND lógico del byte alto de IX con el acumulador.
DD A5       	AND   IXL       2 AND lógico del byte bajo de IX con el acumulador.
FD A4       	AND   IYH       2 AND lógico del byte alto de IY con el acumulador.
FD A5       	AND   IYL       2 AND lógico del byte bajo de IY con el acumulador.
A6          	AND   (HL)      2 AND lógico del valor en la ubicación HL con el acumulador.
DD A6 hh    	AND   (IX+d)    5 AND lógico del valor en la ubicación IX+d con el acumulador.
FD A6 hh    	AND   (IY+d)    5 AND lógico del valor en la ubicación IY+d con el acumulador.

CB bF       	BIT   b,A       2 Chequea si el bit b del registro r es 1.
CB b8       	BIT   b,B         El resultado queda en el flag Z.
CB b9       	BIT   b,C
CB bA       	BIT   b,D
CB bB       	BIT   b,E
CB bC       	BIT   b,H
CB bD       	BIT   b,L
CB bE       	BIT   b,(HL)    3 Chequea si el bit b del valor en la ubicación HL es 1.
DD CB hh bE 	BIT   b,(IX+d)  6 Chequea si el bit b del valor en la ubicación IX+d.
FD CB hh bE 	BIT   b,(IY+d)  6 Chequea si el bit b del valor en la ubicación IY+d.

CD hh HH    	CALL  HHhh      5 Llama a la subrutina en la dirección de memoria dada.
CC hh HH    	CALL  z,HHhh  3/5 Llama a la subrutina si el flag Z es 1, si no (3).
C4 hh HH    	CALL  nz,HHhh 3/5 Llama a la subrutina si el flag Z es 0, si no (3).
DC hh HH    	CALL  c,HHhh  3/5 Llama a la subrutina si el flag C es 1, si no (3).
D4 hh HH    	CALL  nc,HHhh 3/5 Llama a la subrutina si el flag C es 0, si no (3).
F4 hh HH    	CALL  p,HHhh  3/5 Llama a la subrutina si el flag S es 0, si no (3).
FC hh HH    	CALL  m,HHhh  3/5 Llama a la subrutina si el flag S es 1, si no (3).
EC hh HH    	CALL  pe,HHhh 3/5 Llama a la subrutina si el flag P/V es 1, si no (3).
E4 hh HH    	CALL  po,HHhh 3/5 Llama a la subrutina si el flag P/V es 0, si no (3).

3F          	CCF             1 Invierte el valor del flag de acarreo.

BF          	CP    A         1 Compara el registro r con el acumulador.
B8          	CP    B           El flag Z es 1 si A == N si no, es 0.
B9          	CP    C           El flag C es 1 si A < N si no, es 0 (sin signo)   
BA          	CP    D           El flag S <> P/V si A < N si no, S = P/V (con signo).  
BB          	CP    E               
BC          	CP    H               
BD          	CP    L
FE hh       	CP    n         2 Compara el valor n con el acumulador.
DD BC       	CP    IXH       1 Compara el byte alto de IX con el acumulador.
DD BD       	CP    IXL       1 Compara el byte bajo de IX con el acumulador.
FD BC       	CP    IYH       1 Compara el byte alto de IY con el acumulador.
FD BD       	CP    IYL       1 Compara el byte bajo de IY con el acumulador.
BE          	CP    (HL)      2 Compara el valor de la ubicación en HL con A.
DD BE hh    	CP    (IX+d)    5 Compara el valor de la ubicación en IX+d con A.
FD BE hh    	CP    (IY+d)    5 Compara el valor de la ubicación en IY+d con A.

ED A9       	CPD             5 Compara el valor de la ubicación en HL con A, HL-1, BC-1.
ED B9       	CPDR          5/6 Repite CPD hasta que BC=0 (5), si BC<>0 (6).
ED A1       	CPI             5 Compara el valor de la ubicación en HL con A, HL+1, BC-1.
ED B1       	CPIR          5/6 Repite CPI hasta que BC=0 (5), si BC<>0 (6).
2F          	CPL             1 Invierte los bits del acumulador (complemento a 1).

27          	DAA             1 Ajusta el acumulador según el formato decimal BCD. 

3D          	DEC   A         1 Decrementa el registro r.
05          	DEC   B
0D          	DEC   C
15          	DEC   D
1D          	DEC   E
25          	DEC   H
2D          	DEC   L
DD 25       	DEC   IXH       2 Decrementa el byte alto de IX.
DD 2D       	DEC   IXL       2 Decrementa el byte bajo de IX.
FD 25       	DEC   IYH       2 Decrementa el byte alto de IY.
FD 2D       	DEC   IYL       2 Decrementa el byte bajo de IY.
35          	DEC   (HL)      3 Decrementa el valor de la ubicación en HL.
DD 35 hh    	DEC   (IX+d)    6 Decrementa el valor de la ubicación en IX+d.
FD 35 hh    	DEC   (IY+d)    6 Decrementa el valor de la ubicación en IY+d.
0B          	DEC   BC        2 Decrementa el registro doble rr.
1B          	DEC   DE
2B          	DEC   HL
3B          	DEC   SP
DD 2B       	DEC   IX        3 Decrementa IX.
FD 2B       	DEC   IY        3 Decrementa IY.

F3          	DI              1 Deshabilita las interrupciones (excepto NMI en 0066h).
hh F4       	DJNZ  n       3/4 B-1 y salta de manera relativa si B<>0 (4), si B=0 (3).
FB          	EI              1 Habilita las interrupciones.

08          	EX    AF,AF'    1 Intercambia el contenido de AF y AF'.
EB          	EX    DE,HL     1 Intercambia el contenido de DE y HL.
E3          	EX    (SP),HL   6 Intercambia el valor de la ubicación en SP y HL.
DD E3       	EX    (SP),IX   7 Intercambia el valor de la ubicación en SP e IX.
FD E3       	EX    (SP),IY   7 Intercambia el valor de la ubicación en SP e IX.
D9          	EXX             1 Intercambia el contenido de BC,DE,HL con BC',DE',HL'.

76          	HALT            * Detiene el procesador a la espera de una interrupción.
                                Su tiempo de ejecución es variable.

ED 46       	IM    0         2 Establece el modo de interrupción a 0 (dispositivo externo).
ED 56       	IM    1         2 Establece el modo de interrupción a 1 (rst 38).
ED 5E       	IM    2         2 Establece el modo de interrupción a 2 (salto a vector).

DB hh       	IN    A,(n)     3 Carga el acumulador con un valor del dispositivo/puerto n.
ED 40       	IN    B,(C)     4 Carga el registro r con un valor del dispositivo/puerto en B.
ED 48       	IN    C,(C)       Ver nota [1] al final del listado.
ED 50       	IN    D,(C)
ED 58       	IN    E,(C)
ED 60       	IN    H,(C)
ED 68       	IN    L,(C)

3C          	INC   A         1 Incrementa el valor del registro r.
04          	INC   B
0C          	INC   C
14          	INC   D
1C          	INC   E
24          	INC   H
2C          	INC   L
DD 24       	INC   IXH       2 Incrementa el valor del byte alto de IX.
DD 2C       	INC   IXL       2 Incrementa el valor del byte bajo de IX.
FD 24       	INC   IYH       2 Incrementa el valor del byte alto de IY.
FD 2C       	INC   IYL       2 Incrementa el valor del byte bajo de IY.
34          	INC   (HL)      3 Incrementa el valor en la ubicación de HL.
DD 34 hh    	INC   (IX+d)    6 Incrementa el valor en la ubicación IX+d.
FD 34 hh    	INC   (IY+d)    6 Incrementa el valor en la ubicación IY+d.
03          	INC   BC        2 Incrementa el valor del registro doble rr.
13          	INC   DE
23          	INC   HL
33          	INC   SP
DD 23       	INC   IX        3 Incrementa el valor del registro IX.
FD 23       	INC   IY        3 Incrementa el valor del registro IY

ED AA       	IND             5 (HL) guarda el valor del dispositivo B!![1], HL-1 y B-1!![1].
ED BA       	INDR          5/6 Realiza un IND y repite hasta que B=0 (5), si B<>0 (6) !![1].
ED A2       	INI             5 (HL) guarda el valor del dispositivo B!![1], HL+1, B-1 !![1].
ED B2       	INIR          5/6 Realiza un INI y repite hasta que B=0 (5), si B<>0 (6) !![1].

C3 hh HH    	JP    HHhh      3 Salto incondicional a la dirección HHhh.
E9          	JP    (HL)      1 Salto incondicional a la ubicación en HL.
DD E9       	JP    (IX)      2 Salto incondicional a la ubicación en IX.
FD E9       	JP    (IY)      2 Salto incondicional a la ubicación en IY.
CA hh HH    	JP    z,HHhh    3 Salto a HHhh si el flag Z es 1.
C2 hh HH    	JP    nz,HHhh   3 Salto a HHhh si el flag Z es 0.
DA hh HH    	JP    c,HHhh    3 Salto a HHhh si el flag C es 1.
D2 hh HH    	JP    nc,HHhh   3 Salto a HHhh si el flag C es 0.
F2 hh HH    	JP    p,HHhh    3 Salto a HHhh si el flag S es 0.
FA hh HH    	JP    m,HHhh    3 Salto a HHhh si el flag S es 1.
EA hh HH    	JP    pe,HHhh   3 Salto a HHhh si el flag P/V es 1.
E2 hh HH    	JP    po,HHhh   3 Salto a HHhh si el flag P/V es 0.

18 hh       	JR    n         3 Salto incondicional relativo a PC+n.       
28 hh       	JR    z,n     2/3 Salto relativo a PC+n si el flag Z es 1 (3), si no (2).
20 hh       	JR    nz,n    2/3 Salto relativo a PC+n si el flag Z es 0 (3), si no (2).
38 hh       	JR    c,n     2/3 Salto relativo a PC+n si el flag C es 1 (3), si no (2).
30 hh       	JR    nc,n    2/3 Salto relativo a PC+n si el flag C es 0 (3), si no (2).

7F          	LD    A,A       1 Copia en el acumulador el valor del registro r.
78          	LD    A,B
79          	LD    A,C
7A          	LD    A,D
7B          	LD    A,E
7C          	LD    A,H
7D          	LD    A,L
ED 5F       	LD    A,R       3 Copia en A el valor de R (registro de refresco de memoria).
ED 57       	LD    A,I       3 Copia en A el valor de I (registro de vector de interrupción).
DD 7C       	LD    A,IXH     2 Copia en A el valor del byte alto de IX.
DD 7D       	LD    A,IXL     2 Copia en A el valor del byte bajo de IX.
FD 7C       	LD    A,IYH     2 Copia en A el valor del byte alto de IY.
FD 7D       	LD    A,IYL     2 Copia en A el valor del byte bajo de IY.

47          	LD    B,A       1 Copia en B el valor del registro r.
40          	LD    B,B
41          	LD    B,C
42          	LD    B,D
43          	LD    B,E
44          	LD    B,H
45          	LD    B,L
DD 44       	LD    B,IXH     2 Copia en B el valor del byte alto de IX.
DD 45       	LD    B,IXL     2 Copia en B el valor del byte bajo de IX.
FD 44       	LD    B,IYH     2 Copia en B el valor del byte alto de IY.
FD 45       	LD    B,IYL     2 Copia en B el valor del byte bajo de IY.

4F          	LD    C,A       1 Copia en C el valor del registro r.
48          	LD    C,B
49          	LD    C,C
4A          	LD    C,D
4B          	LD    C,E
4C          	LD    C,H
4D          	LD    C,L
DD 4C       	LD    C,IXH     2 Copia en C el valor del byte alto de IX.
DD 4D       	LD    C,IXL     2 Copia en C el valor del byte bajo de IX.
FD 4C       	LD    C,IYH     2 Copia en C el valor del byte alto de IY.
FD 4D       	LD    C,IYL     2 Copia en C el valor del byte bajo de IY.

57          	LD    D,A       1 Copia en D el valor del registro r.
50          	LD    D,B
51          	LD    D,C
52          	LD    D,D
53          	LD    D,E
54          	LD    D,H
55          	LD    D,L
DD 54       	LD    D,IXH     2 Copia en D el valor del byte alto de IX.
DD 55       	LD    D,IXL     2 Copia en D el valor del byte bajo de IX.
FD 54       	LD    D,IYH     2 Copia en D el valor del byte alto de IY.
FD 55       	LD    D,IYL     2 Copia en D el valor del byte bajo de IY.

5F          	LD    E,A       1 Copia en E el valor del registro r.
58          	LD    E,B
59          	LD    E,C
5A          	LD    E,D
5B          	LD    E,E
5C          	LD    E,H
5D          	LD    E,L
DD 5C       	LD    E,IXH     2 Copia en E el valor del byte alto de IX.
DD 5D       	LD    E,IXL     2 Copia en E el valor del byte bajo de IX.
FD 5C       	LD    E,IYH     2 Copia en E el valor del byte alto de IY.
FD 5D       	LD    E,IYL     2 Copia en E el valor del byte bajo de IY.

67          	LD    H,A       1 Copia en H el valor del registro r.
60          	LD    H,B
61          	LD    H,C
62          	LD    H,D
63          	LD    H,E
64          	LD    H,H
65          	LD    H,L

6F          	LD    L,A       1 Copia en L el valor del registro r.
68          	LD    L,B
69          	LD    L,C
6A          	LD    L,D
6B          	LD    L,E
6C          	LD    L,H
6D          	LD    L,L

ED 47       	LD    I,A       3 Copia en I el valor del acumulador.
ED 4F       	LD    R,A       3 Copia en R el valor del acumulador.

3E hh       	LD    A,n       2 Copia en el registro r el valor n.
06 hh       	LD    B,n
0E hh       	LD    C,n
16 hh       	LD    D,n
1E hh       	LD    E,n
26 hh       	LD    H,n
2E hh       	LD    L,n

7E          	LD    A,(HL)    2 Copia en el registro r el valor en la ubicación de HL.
46          	LD    B,(HL)
4E          	LD    C,(HL)
56          	LD    D,(HL)
66          	LD    H,(HL)
6E          	LD    L,(HL)

DD 7E hh    	LD    A,(IX+d)  5 Copia en el registro r el valor en la ubicación de IX+d.
DD 46 hh    	LD    B,(IX+d)
DD 4E hh    	LD    C,(IX+d)
DD 56 hh    	LD    D,(IX+d)
DD 5E hh    	LD    E,(IX+d)
DD 66 hh    	LD    H,(IX+d)
DD 6E hh    	LD    L,(IX+d)
FD 7E hh    	LD    A,(IY+d)  5 Copia en el registro r el valor en la ubicación de IY+d.
FD 46 hh    	LD    B,(IY+d)
FD 4E hh    	LD    C,(IY+d)
FD 56 hh    	LD    D,(IY+d)
FD 5E hh    	LD    E,(IY+d)
FD 66 hh    	LD    H,(IY+d)
FD 6E hh    	LD    L,(IY+d)

0A          	LD    A,(BC)    2 Copia en el acumulador el valor en la ubicación de BC.
1A          	LD    A,(DE)    2 Copia en el acumulador el valor en la ubicación de DE.
3A hh HH    	LD    A,(HHhh)  4 Copia en el acumulador el valor en la ubicación HHhh.

F9          	LD    SP,HL     2 Copia en SP el valor de HL.
DD F9       	LD    SP,IX     3 Copia en SP el valor de IX.
FD F9       	LD    SP,IY     3 Copia en SP el valor de IY.
31 hh HH    	LD    SP,nn     3 Copia en SP el valor nn.
ED 7B hh HH 	LD    SP,(HHhh) 6 Copia en SP el valor en la ubicación HHhh.

01 hh HH    	LD    BC,nn     3 Copia en el registro doble rr el valor nn.
11 hh HH    	LD    DE,nn
21 hh HH    	LD    HL,nn
DD 21 hh HH 	LD    IX,nn     4 Copia en IX el valor nn.
FD 21 hh HH 	LD    IY,nn     4 Copia en IY el valor nn.

ED 4B hh HH 	LD    BC,(HHhh) 6 Copia en el registro doble rr el valor en la ubicación HHhh.
ED 5B hh HH 	LD    DE,(HHhh)
2A hh HH    	LD    HL,(HHhh)
DD 2A hh HH 	LD    IX,(HHhh) 6 Copia en IX el valor en la ubicación HHhh.
FD 2A hh HH 	LD    IY,(HHhh) 6 Copia en IY el valor en la ubicación HHhh.

02          	LD    (BC),A    2 Copia en la ubicación de rr el valor en r.
12          	LD    (DE),A
77          	LD    (HL),A
70          	LD    (HL),B
71          	LD    (HL),C
72          	LD    (HL),D
73          	LD    (HL),E
74          	LD    (HL),H
75          	LD    (HL),L
36 hh       	LD    (HL),n    3 Copia en la ubicación de HL el valor n.
DD 36 dd nn 	LD    (IX+d),n  6 Copia en la ubicación de IX+d el valor n.
DD 77 hh    	LD    (IX+d),A  5 Copia en la ubicación de IX+d el valor del registro r.
DD 70 hh    	LD    (IX+d),B
DD 71 hh    	LD    (IX+d),C
DD 72 hh    	LD    (IX+d),D
DD 73 hh    	LD    (IX+d),E
DD 74 hh    	LD    (IX+d),H
DD 75 hh    	LD    (IX+d),L
FD 36 dd nn 	LD    (IY+d),n  6 Copia en la ubicación de IY+d el valor n.
FD 77 hh    	LD    (IY+d),A  5 Copia en la ubicación de IY+d el valor del registro r.
FD 70 hh    	LD    (IY+d),B
FD 71 hh    	LD    (IY+d),C
FD 72 hh    	LD    (IY+d),D
FD 73 hh    	LD    (IY+d),E
FD 74 hh    	LD    (IY+d),H
FD 75 hh    	LD    (IY+d),L

32 hh HH    	LD    (HHhh),A  4 Copia en la ubicación HHhh el valor del acumulador.
22 hh HH    	LD    (HHhh),HL 5 Copia en la ubicación HHhh el valor de HL.
ED 43 hh HH 	LD    (HHhh),BC 6 Copia en la ubicación HHhh el valor del registro doble rr.
ED 53 hh HH 	LD    (HHhh),DE
DD 22 hh HH 	LD    (HHhh),IX
FD 22 hh HH 	LD    (HHhh),IY
ED 73 hh HH 	LD    (HHhh),SP

ED A8       	LDD             5 Copia en (DE) el valor de la ubicación en HL, DE-1, HL-1, BC-1.
ED B8       	LDDR          5/6 Repite LDD hasta que BC=0 (5), si BC<>0 (6).
ED A0       	LDI             5 Copia en (DE) el valor de la ubicación en HL, DE+1, HL+1, BC-1.
ED B0       	LDIR          5/6 Repite LDI hasta que BC=0 (5), si BC<>0 (6).

ED 44       	NEG             2 Cambia el signo del acumulador (complemento a 2).
00          	NOP             1 Operación vacía (No Operation).

B7          	OR    A         1 OR lógico entre el registro r y el acumulador.
B0          	OR    B
B1          	OR    C
B2          	OR    D
B3          	OR    E
B4          	OR    H
B5          	OR    L
DD B4       	OR    IXH       2 OR lógico entre el byte alto de IX y el acumulador.
DD B5       	OR    IXL       2 OR lógico entre el byte bajo de IX y el acumulador.
FD B4       	OR    IYH       2 OR lógico entre el byte alto de IY y el acumulador.
FD B5       	OR    IYL       2 OR lógico entre el byte bajo de IY y el acumulador.
F6 hh       	OR    n         2 OR lógico entre el valor n y el acumulador.
B6          	OR    (HL)      2 OR lógico entre el valor en la ubicación de HL y A.
DD B6 hh    	OR    (IX+d)    5 OR lógico entre el valor en la ubicación de IX+d y A.
FD B6 hh    	OR    (IY+d)    5 OR lógico entre el valor en la ubicación de IY+d y A.
 
ED BB       	OTDR          5/6 Repite OUTD hasta que B=0 (5), si B<>0 (6)[1].
ED B3       	OTIR          5/6 Repite OTI hasta que B=0 (5), si B<>0 (6)[1].
ED 79       	OUT   (C),A     4 Escribe en el puerto de salida almacenado en B el valor de r.
ED 49       	OUT   (C),C       Revisar la nota [1] al final del listado.
ED 51       	OUT   (C),D
ED 59       	OUT   (C),E
ED 61       	OUT   (C),H
ED 69       	OUT   (C),L
D3 hh       	OUT   (n),A     3 Escribe en el puerto de salida n el valor de A [1].
ED AB       	OUTD            5 Escribe el valor de la ubicación de HL
                                en el puerto de salida indicado por B(!!), HL-1, B-1[1].
ED A3       	OUTI            5 Escribe el valor de la ubicación de HL 
                                en el puerto de salida indicado por B(!!), HL+1, B-1[1].

F1          	POP   AF        3 Copia en el registro doble rr el último valor de la pila.
C1          	POP   BC
D1          	POP   DE
E1          	POP   HL
DD E1       	POP   IX        5 Copia en IX el último valor de la pila.
FD E1       	POP   IY        5 Copia en IY el último valor de la pila.

F5          	PUSH  AF        4 Copia en la pila el valor del registro doble rr.
C5          	PUSH  BC
D5          	PUSH  DE
E5          	PUSH  HL
DD E5       	PUSH  IX        5 Copia en la pila el valor de IX.
FD E5       	PUSH  IY        5 Copia en la pila el valor de IY.

CB **       	RES   b,A       2 Pone a 0 el bit b del registro r.
CB **       	RES   b,B         ** El último byte codifica el bit y el
CB **       	RES   b,C            registro. Los valores empiezan en 80 y
CB **       	RES   b,D            terminan en BF, el byte se compone como:
CB **       	RES   b,E            1 0 b b b r r r
CB **       	RES   b,H            b = [0-7]
CB **       	RES   b,L            r = B=0, C, D, E, H, L, A=7
CB **       	RES   b,(HL)    4 Pone a 0 el bit b del valor en la ubicación de HL.
DD CB hh ** 	RES   b,(IX+d)  7 Pone a 0 el bit b del valor en la ubicación de IX+d.
FD CB hh ** 	RES   b,(IY+d)  7 Pone a 0 el bit b del valor en la ubicación de IY+d.

C9          	RET             3 Retorna de la subrutina.
C8          	RET   z       2/4 Retorna de la subrutina si el flag Z es 1 (4) si no (2).
C0          	RET   nz      2/4 Retorna de la subrutina si el flag Z es 0 (4) si no (2).
D8          	RET   c       2/4 Retorna de la subrutina si el flag C es 1 (4) si no (2).
D0          	RET   nc      2/4 Retorna de la subrutina si el flag C es 0 (4) si no (2).
F0          	RET   p       2/4 Retorna de la subrutina si el flag S es 0 (4) si no (2).
F8          	RET   m       2/4 Retorna de la subrutina si el flag S es 1 (4) si no (2).
E8          	RET   pe      2/4 Retorna de la subrutina si el flag P/V es 1 (4) si no (2).
E0          	RET   po      2/4 Retorna de la subrutina si el flag P/V es 0 (4) si no (2).

ED 4D       	RETI            4 Retorna de la interrupción.
ED 45       	RETN            4 Retorna de la interrupción no enmascarable.

CB 17       	RL    A         2 Rota a la izquierda el valor del registro r
CB 10       	RL    B           a través del flag C: el bit 7 se mueve al flag
CB 11       	RL    C           de acarreo C y el valor actual de dicho flag
CB 12       	RL    D           se mueve al bit 0.
CB 13       	RL    E
CB 14       	RL    H
CB 15       	RL    L
CB 16       	RL    (HL)      4 Rota a izq. el valor en la ubicación de HL. Usa flag C.
DD CB hh 16 	RL    (IX+d)    7 Rota a izq. el valor en la ubicación de IX+d. Usa flag C.
FD CB hh 16 	RL    (IY+d)    7 Rota a izq. el valor en la ubicación de IY+d. Usa flag C.

17          	RLA             1 Rota a la izquierda el valor en A a través del flag C.

CB 07       	RLC   A         2 Rota el valor de r a la izquierda de manera circular:
CB 00       	RLC   B           el bit 7 se copia tanto al flag de acarreo C como
CB 01       	RLC   C           al bit 0.
CB 02       	RLC   D
CB 03       	RLC   E
CB 04       	RLC   H
CB 05       	RLC   L
CB 06       	RLC   (HL)      4 Rota el valor en (HL) a la izquierda de manera circular.
DD CB hh 06 	RLC   (IX+d)    7 Rota el valor en (IX+d) a la izquierda de manera circular.
FD CB hh 06 	RLC   (IY+d)    7 Rota el valor en (IY+d) a la izquierda de manera circular.

07          	RLCA            1 Rota a la izquierda de manera circular el valor de A.
ED 6F       	RLD             5 Rota a la izq. de forma circular cuatro bits (nibble):
                                nibble bajo A -> nibble bajo (HL) -> nibble alto (HL) ->
                                nibble bajo A.

CB 1F       	RR    A         2 Rota a la derecha el valor del registro r
CB 18       	RR    B           a través del flag C: el bit 0 se mueve al flag
CB 19       	RR    C           de acarreo C y el valor actual de dicho flag
CB 1A       	RR    D           se mueve al bit 7.
CB 1B       	RR    E
CB 1C       	RR    H
CB 1D       	RR    L
CB 1E       	RR    (HL)      4 Rota a der. el valor en la ubicación de HL. Usa flag C.
DD CB hh 1E 	RR    (IX+d)    7 Rota a der. el valor en la ubicación de IX+d. Usa flag C.
FD CB hh 1E 	RR    (IY+d)    7 Rota a der. el valor en la ubicación de IY+d. Usa flag C.

1F          	RRA             1 Rota a la derecha el valor de A a través del flag C.

CB 0F       	RRC   A         2 Rota el valor de r a la derecha de manera circular:
CB 08       	RRC   B           el bit 0 se copia tanto al flag de acarreo C como
CB 09       	RRC   C           al bit 7.
CB 0A       	RRC   D
CB 0B       	RRC   E
CB 0C       	RRC   H
CB 0D       	RRC   L
CB 0E       	RRC   (HL)      4 Rota el valor en (HL) a la der. de manera circular.
DD CB hh 0E 	RRC   (IX+d)    7 Rota el valor en (IX+d) a la der. de manera circular.
FD CB hh 0E 	RRC   (IY+d)    7 Rota el valor en (IY+d) a la der. de manera circular.

0F          	RRCA            1 Rota el valor de A a la derecha de manera circular.
ED 67       	RRD             5 Rota a la der. de forma circular cuatro bits (nibble):
                                nibble bajo A -> nibble alto (HL) -> nibble bajo (HL) ->
                                nibble bajo A.

C7          	RST   &00       4 RESET. Reservado [2]. Reinicia el sistema.
CF          	RST   &08       4 LOW CALL. Reservado [2]. Salta a una rutina en los primeros 16K.
D7          	RST   &10       4 SIDE CALL. Reservado [2]. Llama a una rutina en una ROM.
DF          	RST   &18       4 FAR CALL. Reservado [2]. Llama a una rutina en cualquier pos de memoria.
E7          	RST   &20       4 RAM LAM. Reservado [2]. Lee el byte desde RAM en la dirección de HL.
EF          	RST   &28       4 FIRM JUMP. Reservado [2]. Salta a una rutina en el ROM inferior.
F7          	RST   &30       4 USER RST. Disponible para el usuario.
FF          	RST   &38       4 INTERRUPT. Reservado [2]. Reservado para interrupciones.

9F          	SBC   A,A       1 Resta el registro r del acumulador con acarreo.
98          	SBC   A,B
99          	SBC   A,C
9A          	SBC   A,D
9B          	SBC   A,E
9C          	SBC   A,H
9D          	SBC   A,L
DD 9C       	SBC   A,IXH     2 Resta el byte alto de IX del acumulador con acarreo.
DD 9D       	SBC   A,IXL     2 Resta el byte bajo de IX del acumulador con acarreo.
FD 9C       	SBC   A,IYH     2 Resta el byte alto de IY del acumulador con acarreo.
FD 9D       	SBC   A,IYL     2 Resta el byte bajo de IY del acumulador con acarreo.
DE hh       	SBC   A,n       2 Resta el valor n del acumulador con acarreo.
9E          	SBC   A,(HL)    2 Resta el valor de la ubicación en HL de A con acarreo.
DD 9E hh    	SBC   A,(IX+d)  5 Resta el valor de la ubicación en IX+d de A con acarreo.
FD 9E hh    	SBC   A,(IY+d)  5 Resta el valor de la ubicación en IY+d de A con acarreo.
ED 42       	SBC   HL,BC     4 Resta el registro doble rr de HL con acarreo.
ED 52       	SBC   HL,DE
ED 62       	SBC   HL,HL
ED 72       	SBC   HL,SP

37          	SCF             1 Establece el flag de acarreo (C=1).

CB **       	SET   b,A       2 Establece a 1 el bit b del registro r.
CB **       	SET   b,B         ** El último byte codifica el bit y el
CB **       	SET   b,C            registro. La secuencia empieza en 80
CB **       	SET   b,D            y termina en BF, el byte se compone como:
CB **       	SET   b,E            1 1 b b b r r r
CB **       	SET   b,H            b = [0-7]
CB **       	SET   b,L            r = B=0, C, D, E, H, L, A=7
CB **       	SET   b,(HL)    4 Establece a 1 el bit b del valor en ubicación de HL.
DD CB hh ** 	SET   b,(IX+d)  7 Establece a 1 el bit b del valor en ubicación de IX+d.
FD CB hh ** 	SET   b,(IY+d)  7 Establece a 1 el bit b del valor en ubicación de IY+d.

CB 27       	SLA   A         2 Desplaza el registro r a la izquierda de manera aritmética.
CB 20       	SLA   B           El valor del bit 7 se copia a flag de acarreo C.
CB 21       	SLA   C           El valor del bit 0 se fija a 0.
CB 22       	SLA   D
CB 23       	SLA   E
CB 24       	SLA   H
CB 25       	SLA   L
CB 26       	SLA   (HL)      4 Desplaza el valor en (HL) a la izq. Bit 0 = 0.
DD CB hh 26 	SLA   (IX+d)    7 Desplaza el valor en (IX+d) a la izq. Bit 0 = 0.
FD CB hh 26 	SLA   (IY+d)    7 Desplaza el valor en (IY+d) a la izq. Bit 0 = 0.

CB 37       	SLL   A         2 Desplaza el registro r a la izquierda de forma "lógica".
CB 30       	SLL   B           El valor del bit 7 se copia en el flag de acarreo C.
CB 31       	SLL   C           El valor del bit 0 se fija a 1.
CB 32       	SLL   D
CB 33       	SLL   E
CB 34       	SLL   H
CB 35       	SLL   L
CB 36       	SLL   (HL)      4 Desplaza el valor en (HL) a la izquierda Bit 0 = 1.
DD CB hh 36 	SLL   (IX+d)    7 Desplaza el valor en (IX+d) a la izquierda Bit 0 = 1.
FD CB hh 36 	SLL   (IY+d)    7 Desplaza el valor en (IY+d) a la izquierda Bit 0 = 1.

CB 2F       	SRA   A         2 Desplaza el valor de r a la derecha de forma aritmética.
CB 28       	SRA   B           El valor del bit 0 se copia en el flag de acarreo C.
CB 29       	SRA   C           El valor del bit 7 se fija a 0.
CB 2A       	SRA   D
CB 2B       	SRA   E
CB 2C       	SRA   H
CB 2D       	SRA   L
CB 2E       	SRA   (HL)      4 Desplaza el valor en (HL) a la derecha. Bit 7 = 0.
DD CB hh 2E 	SRA   (IX+d)    7 Desplaza el valor en (IX+d) a la derecha. Bit 7 = 0.
FD CB hh 2E 	SRA   (IY+d)    7 Desplaza el valor en (IY+d) a la derecha. Bit 7 = 0.


CB 3F       	SRL   A         2 Desplaza el registro r a la derecha de forma "lógica".
CB 38       	SRL   B           El bit 0 se copia al flag C (acarreo).
CB 39       	SRL   C           El bit 7 se fija a 1.
CB 3A       	SRL   D
CB 3B       	SRL   E
CB 3C       	SRL   H
CB 3D       	SRL   L
CB 3E       	SRL   (HL)      4 Desplaza el valor en (HL) a la derecha. Bit 7 = 1.
DD CB hh 3E 	SRL   (IX+d)    7 Desplaza el valor en (IX+d) a la derecha. Bit 7 = 1.
FD CB hh 3E 	SRL   (IY+d)    7 Desplaza el valor en (IY+d) a la derecha. Bit 7 = 1.

97          	SUB   A         1 Resta el valor del registro r del acumulador.
90          	SUB   B
91          	SUB   C
92          	SUB   D
93          	SUB   E
94          	SUB   H
95          	SUB   L
D6 hh       	SUB   n         2 Resta el valor n del acumulador.
DD 94       	SUB   IXH       2 Resta el byte alto de IX del acumulador.
DD 95       	SUB   IXL       2 Resta el byte bajo de IX del acumulador.
FD 94       	SUB   IYH       2 Resta el byte alto de IY del acumulador.
FD 95       	SUB   IYL       2 Resta el byte bajo de IY del acumulador.
96          	SUB   (HL)      2 Resta el valor de la ubicación en HL del acumulador.
DD 96 hh    	SUB   (IX+d)    5 Resta el valor de la ubicación en IX+d del acumulador.
FD 96 hh    	SUB   (IY+d)    5 Resta el valor de la ubicación en IY+d del acumulador.

AF          	XOR   A         1 Realiza una OR exclusiva entre el registro r y A.
A8          	XOR   B
A9          	XOR   C
AA          	XOR   D
AB          	XOR   E
AC          	XOR   H
AD          	XOR   L
EE hh       	XOR   n         2 Realiza una OR exclusiva entre el valor n y A.
DD AC       	XOR   IXH       2 Realiza una OR exclusiva entre el byte alto de IX y A.
DD AD       	XOR   IXL       2 Realiza una OR exclusiva entre el byte bajo de IX y A.
FD AC       	XOR   IYH       2 Realiza una OR exclusiva entre el byte alto de IY y A.
FD AD       	XOR   IYL       2 Realiza una OR exclusiva entre el byte bajo de IY y A.
AE          	XOR   (HL)      2 Realiza una OR exclusiva entre el valor en (HL) y A.
DD AE hh    	XOR   (IX+d)    5 Realiza una OR exclusiva entre el valor en (IX+d) y A.
FD AE hh    	XOR   (IY+d)    5 Realiza una OR exclusiva entre el valor en (IY+d) y A.
```

**[1]** Es importante recordar que las instrucciones de la familia OUT/IN utilizan el contenido de `BC` y no solo `C`, incluso si el código de operación es `OUT (C)`. En el Amstrad CPC, las instrucciones OUTD, OUTI, OTIR, etc., no tienen mucho sentido porque el AMSTRAD CPC utiliza el valor de `B`(!!) del registro doble `BC` para indicar el número del puerto y no `C`, como hacen muchas otras máquinas basadas en el Z80.

**[2]** Todas las instrucciones RST del Z80, excepto una, han sido reservadas para uso del sistema. De RST 1 a RST 5 (&08-&28) se utilizan para extender el conjunto de instrucciones añadiendo instrucciones específicas de llamada y salto que habilitan y deshabilitan los ROMs. RST 6 (&30) está disponible para el usuario. Se puede obtener más información sobre el uso de la instrucción RST aquí: [ROMs. RAM and Restart Instructions.](https://www.cpcwiki.eu/imgs/f/f6/S968se02.pdf)

# Historial de cambios

- Versión 1.4.4
  * Pequeñas mejoras y arreglos.
  
- Versión 1.4.3
  * Arreglos en algunos mensajes de error en la herramienta DSK.
  * Arreglada la codificación de bloques raw en la herramienta CDT.
  * Otras pequeñas mejoras y arreglos.

- Versión 1.4.2
  * Eliminamos los finales de línea ya que pueden afectar a los mensajes de error.
  * La herramienta DSK permite indicar el usuario y añadir los flags read-only y system.

- Versión 1.4.1 - 09/02/2026
  * Pequeños arreglos en la biblioteca CPCTELERA
  * Mejores mensajes de error en las herramientas CDT/DSK
  * Soporte para procesar multiples ficheros en IMG

- Versión 1.4.0 - 07/01/2026
  * Añadida la directiva IFNOT
  * Añadida la herramienta `IMG`

- Versión 1.3.1 - 28/12/2025
  * Los ejemplos de CPCTELERA no estaban funcionando desde el DSK.
  * Arreglo en los finales de línea de los ficheros ASCII añadidos a ficheros DSK o CDT.
  * Se ha añadido un Make.sh en todos los ejemplos para su uso en Linux o macOS.

- Versión 1.3.0 - 27/12/2025
  * Nueva directiva MDELETE para eliminar la definición de una macro.
  * Arreglado un problema con el uso de macros sin parámetros.
  * Abasm muestra el mensaje de error adecuado si se usan las directivas REPEAT o WHILE dentro de una macro.
  * Port de la biblioteca CPCTELERA como nuevo ejemplo de bibliotecas en ABASM.
  * Nueva herramientas ASMPRJ para crear una estructura básica de proyecto.

- Versión 1.2.0 - 15/12/2025
  * Soporte para el uso de bibliotecas, ficheros .asm situados dentro del directorio `lib` de la distribución ABASM.
  * Port de parte de la biblioteca CPCRSLIB como ejemplo del nuevo soporte a bibliotecas. Se pueden ver varios ejemplos de su uso en `examples/cpcrslib`.
  * Nuevo flag `-s` `--sfile` que genera un único fichero .s con todo el código ensamblado, incluyendo el código importando de otros ficheros.
  * Mejora en la gestión de múltiples directivas ORG
  * Importa solo una vez un mismo fichero .ASM referenciado multiples veces por READ o INCLUDE
  * Otras pequeñas mejoras.

- Version 1.1.3 - 16/04/2025
  * Se ha añadido la utilidad bindiff para comparar binarios.
  * Se ha corregido un error en la directiva ELSEIF.
  * Se ha añadido la opción `--tolerance` para poder suprimir *warnings* o convertirlos en errores.
  * Otros pequeños arreglos y mejoras.
  
- Versión 1.1.2 - 26/03/2025
  * El listado de instrucciones del Z80 include ahora el código máquina asociado.
  * Se han Arreglado las expresiones matemáticas con carácteres en la directiva DB.
  * Otros pequeños arreglos y mejoras.

- Versión 1.1.1 - 09/03/2025
  * No se reconocía la familia de opcodes SLL.
  * EX AF,AF' daba error.
  * Se ha añadido la sección `Conjunto de Instrucciones del Z80` a los manuales.
  * Otros pequeños arreglos y mejoras. 

- Versión 1.1.0 - 06/03/2025
  * Soporte para la directiva LIMIT.
  * Soporte de etiquetas locales dentro del código de las macros.
  * Añadido el flag --verbose como opción al ensamblador.
  * Añadidos tests ejecutables mediante python -m unittest
  * Otros pequeños arreglos y mejoras.

- Versión 1.0.0 - 03/10/2024
  * Primera versión liberada.
