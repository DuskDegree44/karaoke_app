import os
import shutil
from multiprocessing import freeze_support
from pathlib import Path
import sys

CUDA_BIN = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.2/bin")
PYTHON_SITE = Path(sys.prefix) / "Lib/site-packages"
CUDA_DLL_DIRS = [
	CUDA_BIN,
	PYTHON_SITE / "nvidia/cudnn/bin",
	PYTHON_SITE / "nvidia/cublas/bin",
	PYTHON_SITE / "nvidia/cuda_nvrtc/bin",
]
for dll_dir in CUDA_DLL_DIRS:
	if dll_dir.exists():
		os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")
		if hasattr(os, "add_dll_directory"):
			os.add_dll_directory(str(dll_dir))

from spleeter.separator import Separator


def main():
	if len(sys.argv) != 2:
		raise SystemExit("Uso: python split.py <audio>")

	input_file = Path(sys.argv[1])
	output_folder = input_file.parent / "output"
	ffmpeg_root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe"
	ffmpeg_files = list(ffmpeg_root.glob("ffmpeg-*/bin/ffmpeg.exe"))
	if not ffmpeg_files:
		raise RuntimeError("FFmpeg no está instalado o no se encontró su ejecutable.")
	os.environ["PATH"] = str(ffmpeg_files[0].parent) + os.pathsep + os.environ.get("PATH", "")

	separator = Separator("spleeter:2stems")
	separator.separate_to_file(str(input_file), str(output_folder))

	instrumental = output_folder / input_file.stem / "accompaniment.wav"
	vocals = output_folder / input_file.stem / "vocals.wav"
	instrumental_copy = input_file.parent / "instrumental.wav"
	vocals_copy = input_file.parent / "voz.wav"
	shutil.copy2(instrumental, instrumental_copy)
	shutil.copy2(vocals, vocals_copy)
	print("Instrumental generado:", instrumental_copy)
	print("Voz generada:", vocals_copy)


if __name__ == "__main__":
	freeze_support()
	main()
