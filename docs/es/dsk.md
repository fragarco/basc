# dsk.py

## Descripción
`dsk.py` es una herramienta simple basada en Python 3.X para crear y gestionar archivos DSK como los utilizados en simuladores y emuladores de disquetera para ordenadores Amstrad CPC. Puede realizar varias operaciones para trabajar con estos archivos, siendo su principal objetivo ayudar en el empaquetado de programas desarrollados desde ordenadores modernos.

Actualmente solo soporta el formato de datos de una cara:
 * 178 kb.
 * 40 pistas con 9 sectores de 512 bytes cada uno.
 * Sectores numerados del 0xC1 al 0xC9.
 * Taba de ficheros con 64 entradas.
 
Para más información sobre el formato se pueden consultar las siguientes páginas:
- [Amstrad CPC Emulator Documentation](http://www.benchmarko.de/cpcemu/cpcdoc/chapter/cpcdoc7_e.html#I_FILE_STRUCTURE)
- [CPCWiki - DSK Disk Image File Format](https://www.cpcwiki.eu/index.php/Format:DSK_disk_image_file_format)
- [Sinclair Wiki - DSK Format](https://sinclair.wiki.zxnet.co.uk/wiki/DSK_format)

Esta herramienta no sobreescribe ficheros existentes con el mismo nombre dentro del fichero DSK, todas las operaciones añaden ficheros. Por eso, se puede combinar la opción --new con las operaciones de insertado, de forma que se pueda generar el mismo fichero DSK cada vez que se ejecute el comando. 

## Uso básico

> python dsk.py <dskfile> [opciones]

## Opciones disponibles

- `--new`: Crea un nuevo archivo DSK vacío.
- `--check`: Verifica si el formato del archivo DSK es compatible con la herramienta.
- `--dump`: Muestra información sobre el formato del archivo DSK en la salida estándar.
- `--cat`: Lista el contenido del archivo DSK en la salida estándar.
- `--header <entry>`: Muestra el encabezado AMSDOS para la entrada de archivo indicada (comenzando en 0).
- `--get <entry>`: Extrae el archivo apuntado por la entrada indicada (comenzando en 0).
- `--put-bin <file>`: Agrega un nuevo archivo binario al archivo DSK, generando y añadiendo un encabezado AMSDOS adicional.
- `--put-raw <file>`: Agrega un nuevo archivo binario al archivo DSK sin crear un encabezado AMSDOS adicional.
- `--put-ascii <file>`: Agrega un nuevo archivo ASCII al archivo DSK. El archivo no debe incluir encabezado AMSDOS.
- `--load-addr <address>`: Dirección inicial para cargar el archivo (por defecto 0x4000, solo en archivos binarios con encabezados AMSDOS generados).
- `--start-addr <address>`: Dirección de llamada después de cargar el archivo (por defecto 0x4000, solo en archivos binarios con encabezados AMSDOS generados).
- `--help`: Muestra la ayuda en la salida estándar.

## Ejemplos de uso

Crear un nuevo archivo DSK con un programa en BASIC

> python dsk.py archivo.dsk --new --put-ascii programa.bas

Listar el contenido del archivo DSK para verificar que nuestro programa está incluido

> python dsk.py archivo.dsk --cat

Crear un fichero DSK con un programa binario que debe cargarse y ejecutarse en la dirección 0x4000

> python dsk.py --new archivo.dsk --new --put-bin programa.bin --load-addr 0x4000 --start-addr 0x4000

