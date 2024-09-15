# Descripción
`cdt.py` es una herramienta simple basada en Python 3.X para crear y gestionar archivos CDT utilizados en simuladores y emuladores de cintas para ordenadores Amstrad CPC. Puede realizar varias operaciones para trabajar con estos archivos, siendo su principal objetivo ayudar en el empaquetado de programas desarrollados desde ordenadores modernos.

Se puede consultar información adicional sobre el formato CDT en el siguiente enlace:
- [The CDT Tape Image File Format](https://www.cpcwiki.eu/index.php/Format:CDT_tape_image_file_format)

Para saber más sobre como la información se almacenaba en cintas reales, se puede consultar el manual sobre el Firmware del Amstrad CPC en el siguiente enlace:
- [The Amstrad Firmware manual](https://archive.org/details/SOFT968TheAmstrad6128FirmwareManual)

Esta herramienta no sobreescribe ficheros existentes con el mismo nombre dentro del fichero CDT, todas las operaciones añaden ficheros. Por eso, se puede combinar la opción --new con las operaciones de insertado, de forma que se pueda generar el mismo fichero CDT cada vez que se ejecute el comando.

# Uso básico

> python3 cdt.py <cdtfile> [opciones]

## Opciones disponibles
- `--new`: Crea un nuevo archivo CDT vacío.
- `--check`: Verifica si el formato del archivo CDT es compatible con la herramienta.
- `--cat`: Lista en la salida estándar todos los bloques actualmente presentes en el archivo CDT.
- `--put-bin <file>`: Agrega un nuevo archivo binario/básico al archivo CDT.
- `--put-ascii <file>`: Agrega un nuevo archivo ASCII al archivo CDT.
- `--put-raw <file>`: Agrega el archivo directamente dentro de un bloque de datos sin ningún encabezado.
- `--map-file <file>`: Importa un archivo generado por el ensamblador ABASM con un listado de símbolos y su dirección de memoria asociada.
- `--load-addr <address>`: Dirección inicial para cargar el archivo.
- `--start-addr <address|symbol>`: Dirección de llamada después de cargar el archivo (por defecto 0x4000). Si se importa un archivo MAP con símbolos se puede indicar uno de dichos símbolos como punto de inicio. Solo tiene uso en archivos binarios con encabezados AMSDOS.
- `--name <name>`: Nombre que se mostrará al cargar el archivo binario/ASCII.
- `--speed <speed>`: Velocidad de escritura: 0 = 1000 baudios, 1 (predeterminado) = 2000 baudios.

## Ejemplos de uso

Crear un nuevo archivo CDT con un programa BASIC:

```
python3 cdt.py archivo.cdt --new --put-ascii programa.bas
```

Listar los bloques en el archivo CDT:

```
python3 cdt.py archivo.cdt --cat
```

Agregar un archivo binario al archivo CDT que muestre el nombre "MIPROGRAMA" al cargar cada bloque:

```
python3 cdt.py archivo.cdt --put-bin programa.bin --load-addr 0x8000 --start-addr 0x8000 --name "MIPROGRAMA"
```

Crear un nuevo fichero CDT y agregar un archivo binario que debe cargarse en la dirección 0x4000 y ejecutarse saltando a la dirección asociada al símbolo MAIN contenido en el archivo simbols.map

```
python3 cdt.py archivo.cdt --new --put-bin programa.bin --map-file simbols.map --load-addr 0x4000 --start-addr MAIN --name "MIPROGRAMA"
```