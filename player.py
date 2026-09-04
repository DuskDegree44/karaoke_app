from pathlib import Path
import os
import time
import tkinter as tk
import wave
from tkinter import filedialog

import customtkinter as ctk
import pygame
import vlc
from PIL import Image, ImageTk


class Player(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Karaoke Studio - Reproductor")
        logo_file = Path(__file__).resolve().parent / "logo.ico"
        if logo_file.exists():
            self.app_icon = ImageTk.PhotoImage(Image.open(logo_file))
            self.iconphoto(True, self.app_icon)
        self.geometry("1000x720")
        self.minsize(700, 560)
        self.configure(fg_color="#10151c")
        self.video_path = None
        self.instrumental_path = None
        self.voice_path = None
        self.vlc_instance = vlc.Instance("--no-video-title-show")
        self.vlc_player = None
        self.base_channel = None
        self.voice_channel = None
        self.audio_ready = False
        self.is_paused = False
        self.after_id = None
        self.initial_sync_id = None
        self.duration = 0
        self.seeking = False
        self.started_at = None
        self.audio_started_at = None
        self.is_playing = False
        self.base_sound = None
        self.voice_sound = None
        self.video_offset_ms = 700
        self.pending_folder_load_id = None
        self.pending_folder_paths = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="REPRODUCTOR", text_color="#72d6c9", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=28, pady=(22, 12), sticky="w")
        self.video_frame = ctk.CTkFrame(self, fg_color="#0b1015")
        self.video_frame.grid(row=1, column=0, padx=28, pady=(0, 14), sticky="nsew")
        self.video_frame.bind("<Configure>", self.resize_video)
        self.timeline = ctk.CTkSlider(self, from_=0, to=1, command=self.preview_position)
        self.timeline.grid(row=2, column=0, padx=28, pady=(0, 2), sticky="ew")
        if hasattr(self.timeline, "_canvas"):
            self.timeline._canvas.bind("<ButtonPress-1>", self.begin_timeline_seek, "+")
            self.timeline._canvas.bind("<ButtonRelease-1>", self.seek_position, "+")
        else:
            self.timeline.bind("<ButtonPress-1>", self.begin_timeline_seek, "+")
            self.timeline.bind("<ButtonRelease-1>", self.seek_position, "+")
        self.time_label = ctk.CTkLabel(self, text="00:00 / 00:00", text_color="#71838d")
        self.time_label.grid(row=3, column=0, padx=28, pady=(0, 8), sticky="w")
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=4, column=0, padx=28, pady=(0, 10), sticky="ew")
        ctk.CTkButton(controls, text="📁", width=42, command=self.import_folder).pack(side="left", padx=(0, 8))
        self.play_button = ctk.CTkButton(controls, text="▶", width=42, command=self.toggle, state="disabled")
        self.play_button.pack(side="left", padx=8)
        ctk.CTkButton(controls, text="■", width=42, command=self.stop).pack(side="left", padx=8)
        ctk.CTkButton(controls, text="−50 ms", width=72, command=self.delay_video).pack(side="left", padx=(24, 4))
        ctk.CTkButton(controls, text="+50 ms", width=72, command=self.advance_video).pack(side="left", padx=4)
        self.offset_label = ctk.CTkLabel(controls, text="Video: 0 ms", text_color="#72d6c9", width=105)
        self.offset_label.pack(side="left", padx=(4, 18))
        self.folder_label = ctk.CTkLabel(controls, text="Sin carpeta", text_color="#71838d")
        self.folder_label.pack(side="left", padx=12)
        volume = ctk.CTkFrame(self, fg_color="transparent")
        volume.grid(row=5, column=0, padx=28, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(volume, text="Volumen voz").pack(side="left")
        self.voice_volume = ctk.CTkSlider(volume, from_=0, to=1, number_of_steps=100, command=self.set_volume)
        self.voice_volume.set(1)
        self.voice_volume.pack(side="left", fill="x", expand=True, padx=12)
        self.volume_label = ctk.CTkLabel(volume, text="100%", width=45)
        self.volume_label.pack(side="right")
        self.fps_label = ctk.CTkLabel(self, text="FPS: VLC / aceleración de video", text_color="#71838d")
        self.fps_label.grid(row=6, column=0, padx=28, pady=(0, 14), sticky="w")
        try:
            os.environ.setdefault("SDL_AUDIODRIVER", "directsound")
            pygame.mixer.init()
            self.base_channel = pygame.mixer.Channel(0)
            self.voice_channel = pygame.mixer.Channel(1)
            self.audio_ready = True
        except pygame.error as error:
            self.folder_label.configure(text=f"Audio no disponible: {error}", text_color="#f07e7e")

    def import_folder(self):
        if self.vlc_player and (self.is_playing or self.is_paused):
            self.folder_label.configure(
                text="Pulsa Stop antes de cambiar de carpeta",
                text_color="#f0a36b",
            )
            return
        folder = filedialog.askdirectory(title="Selecciona una carpeta de conversión")
        if not folder:
            return
        folder = Path(folder)
        paths = (folder / "video_karaoke.mp4", folder / "instrumental.wav", folder / "voz.wav")
        if not all(path.exists() for path in paths):
            self.folder_label.configure(text="Faltan video_karaoke.mp4, instrumental.wav o voz.wav", text_color="#f07e7e")
            return
        try:
            self.stop()
            self.pending_folder_paths = (folder.name, paths)
            if self.pending_folder_load_id:
                self.after_cancel(self.pending_folder_load_id)
            self.pending_folder_load_id = self.after(300, self.finish_folder_load)
        except (OSError, pygame.error, vlc.VLCException) as error:
            self.stop()
            self.folder_label.configure(text=f"No se pudo cargar la carpeta: {error}", text_color="#f07e7e")

    def finish_folder_load(self):
        self.pending_folder_load_id = None
        if not self.pending_folder_paths:
            return
        folder_name, paths = self.pending_folder_paths
        self.pending_folder_paths = None
        try:
            self.video_path, self.instrumental_path, self.voice_path = paths
            self.video_offset_ms = 700
            self.update_offset_label()
            self.folder_label.configure(text=folder_name, text_color="#72d6c9")
            self.play_button.configure(state="normal")
            self.start_video_preview()
        except (OSError, pygame.error, vlc.VLCException) as error:
            self.folder_label.configure(text=f"No se pudo cargar la carpeta: {error}", text_color="#f07e7e")

    def start_video_preview(self):
        media = self.vlc_instance.media_new(str(self.video_path))
        if not self.vlc_player:
            self.vlc_player = self.vlc_instance.media_player_new()
            self.vlc_player.set_hwnd(self.video_frame.winfo_id())
        self.vlc_player.set_media(media)
        self.vlc_player.audio_set_mute(True)
        self.duration = max(1, pygame.mixer.Sound(str(self.instrumental_path)).get_length())
        self.timeline.configure(to=self.duration)
        self.time_label.configure(text=f"00:00 / {self.format_time(self.duration)}")

    def toggle(self):
        if not self.vlc_player:
            return
        if self.is_paused or self.vlc_player.get_state() == vlc.State.Paused:
            self.is_paused = False
            self.is_playing = True
            self.vlc_player.play()
            self.base_channel.unpause()
            self.voice_channel.unpause()
            self.play_button.configure(text="Ⅱ")
            self.update()
        else:
            self.is_paused = True
            self.is_playing = False
            self.vlc_player.pause()
            self.base_channel.pause()
            self.voice_channel.pause()
            self.play_button.configure(text="▶")

    def start_audio(self, position=0, playing=True):
        self.base_sound = self.load_from_position(self.instrumental_path, position)
        self.voice_sound = self.load_from_position(self.voice_path, position)
        self.base_channel.stop()
        self.voice_channel.stop()
        self.base_channel.play(self.base_sound)
        self.voice_channel.play(self.voice_sound)
        self.voice_channel.set_volume(float(self.voice_volume.get()))
        if not playing:
            self.base_channel.pause()
            self.voice_channel.pause()

    def load_from_position(self, path, position):
        with wave.open(str(path), "rb") as audio:
            start = min(int(position * audio.getframerate()), audio.getnframes())
            audio.setpos(start)
            return pygame.mixer.Sound(buffer=audio.readframes(audio.getnframes() - start))

    def begin(self):
        if not self.audio_ready or not self.vlc_player:
            self.folder_label.configure(text="Carga una carpeta con audio y video", text_color="#f07e7e")
            return
        self.is_paused = False
        self.is_playing = True
        try:
            audio_position = max(0, -self.video_offset_ms / 1000)
            video_position = max(0, self.video_offset_ms)
            self.vlc_player.set_time(video_position)
            self.audio_started_at = time.monotonic()
            self.start_audio(audio_position, playing=True)
            pygame.mixer.unpause()
            if not self.base_channel.get_busy() or not self.voice_channel.get_busy():
                raise pygame.error("No se pudieron iniciar los dos canales de audio")
            self.vlc_player.play()
            self.initial_sync_id = self.after(250, self.apply_initial_sync)
        except (pygame.error, OSError) as error:
            self.is_playing = False
            self.folder_label.configure(text=f"Error de audio: {error}", text_color="#f07e7e")
            return
        self.play_button.configure(text="Ⅱ")
        self.update()

    def apply_initial_sync(self):
        self.initial_sync_id = None
        if not self.vlc_player or not self.is_playing:
            return
        audio_elapsed_ms = int((time.monotonic() - self.audio_started_at) * 1000)
        target_ms = max(0, audio_elapsed_ms + self.video_offset_ms)
        self.vlc_player.set_time(target_ms)

    def update(self):
        if not self.vlc_player or self.is_paused:
            return
        position = max(0, self.vlc_player.get_time() / 1000)
        if not self.seeking:
            self.timeline.set(min(position, self.duration))
            self.time_label.configure(text=f"{self.format_time(position)} / {self.format_time(self.duration)}")
        if self.vlc_player.get_state() in (vlc.State.Ended, vlc.State.Error):
            self.stop()
            return
        self.after_id = self.after(33, self.update)

    def toggle_or_begin(self):
        if self.is_playing or self.is_paused:
            self.toggle()
        else:
            self.begin()

    def preview_position(self, value):
        self.seeking = True
        self.time_label.configure(text=f"{self.format_time(float(value))} / {self.format_time(self.duration)}")

    def begin_timeline_seek(self, _event=None):
        self.seeking = True

    def seek_position(self, _event=None):
        if not self.vlc_player:
            return
        position = float(self.timeline.get())
        playing = self.is_playing and not self.is_paused
        self.is_playing = playing
        self.vlc_player.set_time(max(0, int((position + self.video_offset_ms / 1000) * 1000)))
        self.start_audio(position, playing)
        if playing:
            self.vlc_player.play()
            self.base_channel.unpause()
            self.voice_channel.unpause()
        self.time_label.configure(text=f"{self.format_time(position)} / {self.format_time(self.duration)}")
        self.seeking = False

    def delay_video(self):
        self.video_offset_ms -= 50
        self.update_offset_label()
        self.apply_video_offset(-50)

    def advance_video(self):
        self.video_offset_ms += 50
        self.update_offset_label()
        self.apply_video_offset(50)

    def update_offset_label(self):
        if hasattr(self, "offset_label"):
            sign = "+" if self.video_offset_ms > 0 else ""
            self.offset_label.configure(text=f"Video: {sign}{self.video_offset_ms} ms")

    def apply_video_offset(self, delta_ms):
        if not self.vlc_player:
            return
        current_video_time = max(0, self.vlc_player.get_time())
        self.vlc_player.set_time(max(0, current_video_time + delta_ms))

    def set_volume(self, value):
        self.volume_label.configure(text=f"{int(float(value) * 100)}%")
        if self.voice_channel:
            self.voice_channel.set_volume(float(value))

    def resize_video(self, _event=None):
        return

    def format_time(self, value):
        seconds = max(0, int(value))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def stop(self):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.initial_sync_id:
            self.after_cancel(self.initial_sync_id)
            self.initial_sync_id = None
        if self.pending_folder_load_id:
            self.after_cancel(self.pending_folder_load_id)
            self.pending_folder_load_id = None
        if self.vlc_player:
            self.vlc_player.stop()
        if self.base_channel:
            self.base_channel.stop()
        if self.voice_channel:
            self.voice_channel.stop()
        self.base_sound = None
        self.voice_sound = None
        self.is_paused = False
        self.is_playing = False
        self.video_offset_ms = 700
        self.update_offset_label()
        if hasattr(self, "play_button"):
            self.play_button.configure(text="▶")
        if hasattr(self, "timeline"):
            self.timeline.set(0)
        if hasattr(self, "time_label"):
            self.time_label.configure(text=f"00:00 / {self.format_time(self.duration)}")

    def release_video_player(self):
        if self.vlc_player:
            player = self.vlc_player
            self.vlc_player = None
            try:
                player.stop()
                player.release()
            except vlc.VLCException:
                pass


if __name__ == "__main__":
    app = Player()
    app.play_button.configure(command=app.toggle_or_begin)
    app.mainloop()
