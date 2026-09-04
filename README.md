# Karaoke Studio

Aplicacion de escritorio para convertir un video de YouTube en una pista karaoke. El flujo descarga el video, extrae su audio, separa voz e instrumental con Spleeter y genera un video nuevo con la instrumental. Incluye un reproductor VLC independiente para escuchar el video y controlar por separado el volumen de la voz.

## Requisitos

- Windows 10 o superior.
- Python 3.11 para la aplicacion principal, descarga, MoviePy y el reproductor.
- Python 3.10 global para Spleeter y TensorFlow.
- FFmpeg.
- VLC Media Player.
- GPU NVIDIA opcional. Spleeter funciona con CPU, pero una GPU NVIDIA puede acelerar la separacion.

La mezcla de Python 3.10 y 3.11 es intencional: Spleeter/TensorFlow usa dependencias antiguas que no son compatibles con el entorno moderno de la aplicacion.

## Instalacion de Python

Instala Python 3.11 y Python 3.10 desde la pagina oficial:

- https://www.python.org/downloads/

Comprueba las versiones:

```powershell
py -3.11 --version
py -3.10 --version
```

Los comandos de este README usan instalaciones globales y no usan `.venv` ni otro entorno virtual.

## Librerias de Python

### Python 3.11

Instala las dependencias de la interfaz, descarga, video y compilacion:

```powershell
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install customtkinter yt-dlp moviepy opencv-python pygame python-vlc pyinstaller
```

Paquetes principales:

- `customtkinter`: interfaz grafica.
- `yt-dlp`: descarga de videos de YouTube.
- `moviepy`: extraccion y reemplazo de audio/video.
- `opencv-python`: compatibilidad con procesamiento de video previo.
- `pygame`: reproduccion y mezcla de instrumental y voz.
- `python-vlc`: control de VLC desde Python.
- `pyinstaller`: compilacion de ejecutables.

### Python 3.10

Spleeter usa Python 3.10 global, separado de Python 3.11 por compatibilidad de dependencias. No se necesita activar ningun entorno virtual. Instala sus dependencias con:

```powershell
py -3.10 -m pip install --upgrade pip
py -3.10 -m pip install spleeter
```

Para la configuracion usada en este proyecto, Spleeter/TensorFlow necesita NumPy 1.x:

```powershell
py -3.10 -m pip install --force-reinstall numpy==1.23.5
```

Comprueba Spleeter:

```powershell
py -3.10 -c "import numpy; from spleeter.separator import Separator; print('Spleeter OK; NumPy', numpy.__version__)"
```

## Programas externos

### FFmpeg

FFmpeg es necesario para unir video y audio, y tambien para Spleeter. Descarga oficial:

- https://ffmpeg.org/download.html

Comprueba la instalacion:

```powershell
ffmpeg -version
```

El codigo tambien busca la instalacion de WinGet en:

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\
```

### Deno

`yt-dlp` usa Deno como runtime JavaScript para resolver ciertos desafios de YouTube. Descarga oficial:

- https://deno.com/

Comprueba la instalacion:

```powershell
deno --version
```

El codigo tambien busca Deno instalado por WinGet en:

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe\deno.exe
```

### VLC

VLC es el reproductor de video usado por `player.py`. Descarga oficial:

- https://www.videolan.org/vlc/

`python-vlc` controla la instalacion de VLC. Deben estar instalados ambos: el paquete de Python y VLC Media Player.

## CUDA y GPU NVIDIA (opcional)

La GPU solo se utiliza para acelerar la separacion de audio con Spleeter/TensorFlow. La reproduccion de video usa VLC y su propia aceleracion de hardware.

Para la combinación actual de Spleeter/TensorFlow en Windows se usa:

- GPU: NVIDIA GeForce GTX 1650 o compatible.
- CUDA Toolkit 11.2.
- cuDNN 8.x compatible con CUDA 11.2.
- Driver NVIDIA actualizado.

CUDA Toolkit:

- https://developer.nvidia.com/cuda-11-2-2-download-archive

Despues de instalar CUDA y cuDNN, comprueba:

```powershell
nvcc --version
```

El resultado debe indicar `release 11.2`. Para comprobar TensorFlow en Python 3.10:

```powershell
py -3.10 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

Resultado esperado cuando la configuracion funciona:

```text
[PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
```

Si aparece `GPUs: []`, TensorFlow no encontro las DLL de CUDA/cuDNN y Spleeter usara CPU. Los avisos sobre `cudart64_110.dll` o `cudnn64_8.dll` indican que falta configurar CUDA/cuDNN.

## Ejecucion desde Python

Desde la carpeta del proyecto:

```powershell
cd C:\Users\angel\OneDrive\Desktop\karaoke
py -3.11 .\app.py
```

La ventana principal permite:

1. Pegar una URL de video.
2. Pulsar `Convertir`.
3. Esperar las etapas de descarga, extraccion, separacion y generacion.
4. Pulsar `Abrir reproductor` para abrir el reproductor en un proceso independiente.

La ventana del reproductor permite importar una carpeta de conversion y reproducir:

- `video_karaoke.mp4`: imagen del video.
- `instrumental.wav`: pista base.
- `voz.wav`: voz separada con volumen independiente.

Tambien incluye pausa, detener, linea de tiempo, ajuste de sincronizacion en pasos de 50 ms y visualizacion de FPS.

## Archivos del proyecto

- `app.py`: ventana principal, descarga y coordinacion del pipeline.
- `player.py`: reproductor VLC independiente con pygame para las dos pistas de audio.
- `yutu.py`: descarga el video mediante `yt-dlp`.
- `extract.py`: extrae el audio del video usando MoviePy.
- `split.py`: separa voz e instrumental usando Spleeter.
- `NewWav.py`: reemplaza el audio del video por la instrumental.
- `*.spec`: configuraciones de PyInstaller.
- `conversiones/`: carpetas generadas, una por cada video procesado.
- `dist/`: ejecutables compilados.
- `logo.ppm`: icono K usado dentro de las ventanas.
- `logo.ico`: icono K usado por los ejecutables de Windows.
- `pretrained_models/2stems/`: modelo de Spleeter necesario para separar voz e instrumental.

## Estructura de una conversion

Cada URL genera una carpeta con el titulo sanitizado y una marca de tiempo:

```text
conversiones/
└── Titulo del video_20260903_123456/
    ├── video_descargado.mp4
    ├── audio_extraido.wav
    ├── voz.wav
    ├── instrumental.wav
    ├── video_karaoke.mp4
    └── output/
        └── audio_extraido/
            ├── vocals.wav
            └── accompaniment.wav
```

## Compilacion a ejecutables

Instala PyInstaller en Python 3.11:

```powershell
py -3.11 -m pip install --upgrade pyinstaller
```

Compila la aplicacion principal, el reproductor y los scripts que usan Python 3.11:

```powershell
C:/Users/angel/AppData/Local/Programs/Python/Python311/Scripts/pyinstaller.exe --clean --noconfirm .\KaraokeStudio.spec
C:/Users/angel/AppData/Local/Programs/Python/Python311/Scripts/pyinstaller.exe --clean --noconfirm .\player.spec
C:/Users/angel/AppData/Local/Programs/Python/Python311/Scripts/pyinstaller.exe --clean --noconfirm .\yutu.spec
C:/Users/angel/AppData/Local/Programs/Python/Python311/Scripts/pyinstaller.exe --clean --noconfirm .\extract.spec
C:/Users/angel/AppData/Local/Programs/Python/Python311/Scripts/pyinstaller.exe --clean --noconfirm .\NewWav.spec
```

Compila `split.exe` con Python 3.10, porque Spleeter esta instalado alli:

```powershell
C:/Users/angel/AppData/Local/Programs/Python/Python310/python.exe -m pip install --upgrade pyinstaller
C:/Users/angel/AppData/Local/Programs/Python/Python310/Scripts/pyinstaller.exe --clean --noconfirm .\split.spec
```

Comprueba los resultados:

```powershell
Get-ChildItem .\dist -Filter *.exe | Select-Object Name,Length
```

Deben existir:

```text
KaraokeStudio.exe
player.exe
yutu.exe
extract.exe
split.exe
NewWav.exe
```

Para ejecutar la version compilada, todos los ejecutables deben estar juntos en `dist`:

```powershell
.\dist\KaraokeStudio.exe
```

La aplicacion compilada busca automaticamente `player.exe`, `yutu.exe`, `extract.exe`, `split.exe` y `NewWav.exe` junto a `KaraokeStudio.exe`.

## Consolas de diagnostico

Por defecto, la aplicacion compilada oculta las consolas de los procesos auxiliares. Para mostrarlas y colocarlas arriba a la derecha, inicia con:

```powershell
.\dist\KaraokeStudio.exe --showConsoles
```

Desde Python:

```powershell
py -3.11 .\app.py --showConsoles
```

Sin `--showConsoles`, las consolas permanecen ocultas.

## Validacion rapida

Comprueba sintaxis en Python 3.11:

```powershell
py -3.11 -m py_compile .\app.py .\player.py .\yutu.py .\extract.py .\NewWav.py
```

Comprueba sintaxis de Spleeter en Python 3.10:

```powershell
py -3.10 -m py_compile .\split.py
```

Comprueba imports principales:

```powershell
py -3.11 -c "import customtkinter, moviepy, yt_dlp, pygame, vlc; print('Dependencias principales OK')"
py -3.10 -c "from spleeter.separator import Separator; print('Spleeter OK')"
```

## Solucion de problemas

### `No module named ...`

Instala el paquete en el mismo Python que ejecuta el archivo. Por ejemplo:

```powershell
py -3.11 -m pip install paquete
```

Para Spleeter:

```powershell
py -3.10 -m pip install spleeter
```

### `moviepy.editor` no existe

El proyecto usa MoviePy 2.x. El import correcto es:

```python
from moviepy import VideoFileClip
```

### `ffmpeg binary not found`

Comprueba que FFmpeg este instalado y que `ffmpeg.exe` este en el `PATH`. Cierra y abre PowerShell despues de instalarlo.

### `Non 7z archive` al instalar CUDA

El instalador se descargo incompleto. El instalador oficial CUDA 11.2.2 tiene un tamano aproximado de 2.9 GB. Verifica el tamano antes de abrirlo.

### Spleeter se queda en `frame_index`

Spleeter esta procesando el audio. Puede usar CPU para lectura, conversion y escritura aunque la inferencia de TensorFlow use GPU. Comprueba la GPU con:

```powershell
nvidia-smi -l 1
```

### VLC muestra `SetThumbnailClip failed`

Es un aviso del backend de video de Windows y normalmente no impide la reproduccion. Los mensajes `Using D3D11VA` indican decodificacion por hardware.

### La voz y la instrumental no suenan sincronizadas

Usa la linea de tiempo y los botones `+50 ms` y `-50 ms` del reproductor. El reproductor comienza con un desfase configurable y aplica el ajuste a VLC sin modificar los archivos de audio.

## Notas importantes

- Usa solo videos y audio para los que tengas permiso de descarga y procesamiento.
- No cierres la consola si estas ejecutando una version con consola visible y necesitas ver los mensajes del pipeline.
- Para cambiar dependencias, respeta la separacion de Python 3.11 y Python 3.10.
