from pathlib import Path
import sys

from yt_dlp import YoutubeDL

if len(sys.argv) != 3:
	raise SystemExit("Uso: python yutu.py <url> <carpeta-salida>")

url = sys.argv[1]
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "video_descargado.mp4"
deno_file = Path.home() / "AppData/Local/Microsoft/WinGet/Packages/DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe/deno.exe"
ffmpeg_root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe"
ffmpeg_files = list(ffmpeg_root.glob("ffmpeg-*/bin/ffmpeg.exe"))
if not ffmpeg_files:
	raise RuntimeError("FFmpeg no está instalado o no se encontró su ejecutable.")
ffmpeg_dir = ffmpeg_files[0].parent

options = {
	"format": "bestvideo*+bestaudio/best",
	"outtmpl": str(output_file),
	"merge_output_format": "mp4",
	"noplaylist": True,
	"js_runtimes": {"deno": {"path": str(deno_file)}},
	"ffmpeg_location": str(ffmpeg_dir),
}
with YoutubeDL(options) as downloader:
	downloader.download([url])

print(f"Descarga completada: {output_file}")
