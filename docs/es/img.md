## Descripción

`img.py` es una herramienta escrita en Python 3 que convierte imágenes de formatos habituales como **PNG** o **JPEG** a formatos utilizables en proyectos de programación para el **Amstrad CPC**. Los formatos de salida incluyen:

- Archivos binarios puros (`bin`)
- Archivos fuente en **C/C++** (`c`)
- Código ensamblador para **Abasm** (compatible con **WinAPE/MAXAM**) (`asm`)
- Archivos **SCN** para pantallas de carga (`scn`)

El archivo de salida tendrá el mismo nombre que la imagen de entrada, pero con la extensión correspondiente al formato de salida seleccionado.

La herramienta también ajusta la imagen en función del formato de salida y el modo de vídeo del Amstrad CPC. En el caso de archivos **SCN**, la imagen se escala automáticamente a la resolución adecuada, y además se calcula la paleta de colores seleccionando los más predominantes en la imagen y ajustándolos a los colores disponibles en la paleta del Amstrad CPC.

### Modos de vídeo del Amstrad CPC:

- **Modo 0**: 160x200 píxeles, 16 colores
- **Modo 1**: 320x200 píxeles, 4 colores
- **Modo 2**: 640x200 píxeles, 2 colores

## Instalación

Para usar esta herramienta, debes tener **Python 3.x** instalado en tu sistema. Además, `img.py` utiliza la librería de imágenes **Pillow**, que se puede instalar fácilmente usando el gestor de paquetes `pip` con el siguiente comando:

```bash
pip install pillow
```

## Uso básico

La herramienta se ejecuta desde la línea de comandos, tomando como entrada un archivo de imagen (PNG, JPEG, etc.) y convirtiéndolo al formato especificado.

```bash
python img.py <inimg> [--name NAME] [--format FORMAT] [--mode MODE]
```

### Opciones disponibles

- **`<inimg>`**: (Obligatorio) El archivo de imagen de entrada. Puede ser un archivo PNG, JPEG u otro formato compatible.
- **`--name`**: (Opcional) El nombre de referencia para la imagen convertida. Si no se especifica, se usará el nombre del archivo de entrada. Este nombre se usa para generar las etiquetas o variables que referenciarán la imagen en el código generado (opciones C/C++ y ASM).
- **`--format`**: (Opcional) El formato de salida. Los valores válidos son `bin`, `c`, `asm`, `scn`. El valor por defecto es `bin`.
- **`--mode`**: (Opcional) El modo gráfico del Amstrad CPC. Los valores posibles son `0`, `1`, `2`. El valor por defecto es `0`.

## Ejemplos de uso

1. Convertir una imagen PNG a un archivo binario sin cabecera AMSDOS (formato por defecto):

```bash
python img.py imagen.png
```

Este comando convierte `imagen.png` en un archivo binario (`imagen.bin`) sin cabecera AMSDOS, utilizando el modo gráfico 0 con 16 colores.

2. Convertir una imagen JPEG a ensamblador compatible con WinAPE/MAXAM:

```bash
python img.py imagen.jpg --format asm --mode 1
```

Este comando convierte `imagen.jpg` en un archivo ensamblador (`imagen.asm`) preparado para el modo gráfico 1 del Amstrad CPC.

3. Convertir una imagen PNG a un archivo fuente en C para SDCC:

```bash
python img.py imagen.png --format c --name mi_sprite
```

Este comando convierte `imagen.png` en archivos fuente en C (`mi_sprite.h` y `mi_sprite.c`), que pueden ser usados con el compilador SDCC. El nombre `mi_sprite` será utilizado para las variables en el código generado.

4. Convertir una imagen a un archivo SCN para pantallas de carga:

```bash
python img.py portada.png --format scn
```

Este comando convierte `portada.png` en un archivo SCN (`portada.scn`) para usar como pantalla de carga. La imagen se escalará a una resolución de 160x200 (modo gráfico 0) con un máximo de 16 colores.

## Licencia

`img.py` es software libre; puedes redistribuirlo y/o modificarlo bajo los términos de la **GNU General Public License v3**, publicada por la **Free Software Foundation**.

`img.py` se distribuye con la esperanza de que sea útil, pero **SIN NINGUNA GARANTÍA**; ni siquiera la garantía implícita de **COMERCIABILIDAD** o **IDONEIDAD PARA UN PROPÓSITO PARTICULAR**. Consulta la **GNU General Public License** para más detalles.

