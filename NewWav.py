from moviepy import VideoFileClip, AudioFileClip
from pathlib import Path
import sys

if len(sys.argv) != 3:
	raise SystemExit("Uso: python NewWav.py <video> <audio-instrumental>")

video_file = Path(sys.argv[1])
new_audio_file = Path(sys.argv[2])
output_file = video_file.parent / "video_karaoke.mp4"

video = VideoFileClip(video_file)
new_audio = AudioFileClip(new_audio_file)
try:
	video_con_audio = video.with_audio(new_audio.with_duration(video.duration))
	video_con_audio.write_videofile(str(output_file), codec="libx264", audio_codec="aac")
	video_con_audio.close()
finally:
	video.close()
	new_audio.close()

print("Video generado:", output_file)
