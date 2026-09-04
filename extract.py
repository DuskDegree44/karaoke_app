from moviepy import VideoFileClip
from pathlib import Path
import sys

if len(sys.argv) != 2:
	raise SystemExit("Uso: python extract.py <video>")

video_file = Path(sys.argv[1])
audio_file = video_file.parent / "audio_extraido.wav"

clip = VideoFileClip(video_file)
try:
	clip.audio.write_audiofile(audio_file)
finally:
	clip.close()

print("Audio extraído en:", audio_file)
