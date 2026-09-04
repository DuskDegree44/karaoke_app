from pathlib import Path
import ctypes
from ctypes import wintypes
import os
import queue
import re
import subprocess
import sys
import threading
import time
import wave
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

import cv2
import customtkinter as ctk
import pygame
import vlc
from yt_dlp import YoutubeDL
from PIL import Image, ImageTk


BASE_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
MAX_RENDER_SIZE = (960, 540)
SPLITTER_PYTHON = Path.home() / "AppData/Local/Programs/Python/Python310/python.exe"
DENO_FILE = Path.home() / "AppData/Local/Microsoft/WinGet/Packages/DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe/deno.exe"
SHOW_CONSOLES = "--showConsoles" in sys.argv


def position_console(process):
    if not SHOW_CONSOLES:
        return

    user32 = ctypes.windll.user32
    target_pid = process.pid

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def find_window(hwnd, _lparam):
        process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value != target_pid or not user32.IsWindowVisible(hwnd):
            return True
        screen_width = user32.GetSystemMetrics(0)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        user32.SetWindowPos(hwnd, 0, screen_width - width - 12, 12, width, height, 0x0040)
        return False

    def wait_for_console():
        for _ in range(50):
            if not process.poll() and user32.EnumWindows(find_window, 0):
                time.sleep(0.1)

    threading.Thread(target=wait_for_console, daemon=True).start()


def runtime_script(script_name):
    script_path = Path(script_name)
    if getattr(sys, "frozen", False):
        return BASE_DIR / f"{script_path.stem}.exe"
    return BASE_DIR / script_path


def safe_folder_name(title):
    title = re.sub(r'[<>:"/\\|?*]', "", title)
    title = re.sub(r"\s+", " ", title).strip(" .")
    return (title or "video")[:90]


class KaraokeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Karaoke Studio BETA 1.0.1")
        logo_file = BASE_DIR / "logo.ico"
        if logo_file.exists():
            self.app_icon = ImageTk.PhotoImage(Image.open(logo_file))
            self.iconphoto(True, self.app_icon)
        self.geometry("820x700")
        self.minsize(620, 620)
        self.configure(fg_color="#10151c")
        self.events = queue.Queue()
        self.video_capture = None
        self.vlc_instance = vlc.Instance("--no-video-title-show")
        self.vlc_player = None
        self.video_after_id = None
        self.voice_channel = None
        self.base_channel = None
        self.video_fps = 40
        self.video_started_at = None
        self.display_frame_count = 0
        self.display_fps = 0
        self.is_paused = False
        self.player_window = None
        self.player_process = None
        self.loaded_folder = None
        self.audio_ready = False
        self.current_frame = None
        self.video_position = 0
        self.video_duration = 0
        self.seeking = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=42, pady=(38, 18), sticky="ew")
        ctk.CTkLabel(
            header,
            text="KARAOKE STUDIO",
            text_color="#72d6c9",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="By DuskDegree44",
            text_color="#f2f5f7",
            font=ctk.CTkFont(size=23, weight="bold"),
        ).pack(anchor="w", pady=(5, 0))

        content = ctk.CTkFrame(self, fg_color="#18212b", corner_radius=14)
        content.grid(row=1, column=0, padx=42, pady=(0, 24), sticky="nsew")
        content.grid_columnconfigure(0, weight=1)

        self.url_input = ctk.CTkEntry(
            content,
            height=46,
            corner_radius=9,
            border_width=1,
            border_color="#334553",
            fg_color="#111820",
            placeholder_text="URL DE VIDEO",
            placeholder_text_color="#7f929d",
            font=ctk.CTkFont(size=14),
        )
        self.url_input.grid(row=0, column=0, padx=28, pady=(28, 14), sticky="ew")
        self.url_input.bind("<Return>", lambda _event: self.start_conversion())

        self.convert_button = ctk.CTkButton(
            content,
            text="Convertir",
            height=44,
            corner_radius=9,
            fg_color="#36a995",
            hover_color="#2b8c7d",
            text_color="#081411",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_conversion,
        )
        self.convert_button.grid(row=1, column=0, padx=28, pady=(0, 18), sticky="ew")

        self.status_label = ctk.CTkLabel(
            content,
            text="Listo para comenzar",
            text_color="#a9b8c0",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.grid(row=2, column=0, padx=28, pady=(0, 24))
        self.progress_bar = ctk.CTkProgressBar(
            content,
            height=8,
            corner_radius=4,
            progress_color="#36a995",
        )
        self.progress_bar.grid(row=3, column=0, padx=28, pady=(0, 24), sticky="ew")
        self.progress_bar.set(0)
        ctk.CTkButton(
            content,
            text="Abrir reproductor",
            height=40,
            command=self.open_player_window,
        ).grid(row=5, column=0, padx=28, pady=(4, 24), sticky="ew")
        self.after(100, self.process_events)

        try:
            os.environ.setdefault("SDL_AUDIODRIVER", "directsound")
            pygame.mixer.init()
            self.base_channel = pygame.mixer.Channel(0)
            self.voice_channel = pygame.mixer.Channel(1)
            self.audio_ready = True
        except pygame.error:
            self.status_label.configure(text="Audio no disponible en este equipo", text_color="#f0a36b")

    def open_player_window(self):
        if self.player_process and self.player_process.poll() is None:
            return
        executable = runtime_script("player.py")
        command = [str(executable)]
        if executable.suffix.lower() == ".py":
            command = [sys.executable, "-u", str(executable)]
        try:
            self.player_process = subprocess.Popen(
                command,
                cwd=BASE_DIR,
                creationflags=0 if SHOW_CONSOLES else subprocess.CREATE_NO_WINDOW,
            )
            position_console(self.player_process)
            self.status_label.configure(text="Reproductor abierto", text_color="#72d6c9")
        except OSError as error:
            self.player_process = None
            self.status_label.configure(text=f"No se pudo abrir el reproductor: {error}", text_color="#f07e7e")

    def start_conversion(self):
        url = self.url_input.get().strip()
        if not url or not url.startswith(("http://", "https://")):
            self.status_label.configure(text="Introduce una URL valida", text_color="#f0a36b")
            return

        self.convert_button.configure(state="disabled", text="Procesando...")
        self.url_input.configure(state="disabled")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        threading.Thread(target=self.run_pipeline, args=(url,), daemon=True).start()

    def resize_current_frame(self, _event=None):
        if self.current_frame is None or not hasattr(self, "video_label"):
            return
        available_width = min(max(320, self.video_label.winfo_width() - 12), MAX_RENDER_SIZE[0])
        available_height = min(max(180, self.video_label.winfo_height() - 12), MAX_RENDER_SIZE[1])
        frame_height, frame_width = self.current_frame.shape[:2]
        scale = min(available_width / frame_width, available_height / frame_height)
        target_size = (max(1, int(frame_width * scale)), max(1, int(frame_height * scale)))
        frame = cv2.resize(self.current_frame, target_size, interpolation=cv2.INTER_AREA)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        self.video_image = ImageTk.PhotoImage(image=image)
        self.video_label.configure(image=self.video_image, text="")

    def toggle_playback(self):
        if self.vlc_player is None:
            self.start_playback()
        elif self.is_paused:
            self.is_paused = False
            self.play_button.configure(text="Ⅱ")
            self.vlc_player.play()
            self.base_channel.unpause()
            self.voice_channel.unpause()
            self.update_video_frame()
        else:
            self.is_paused = True
            self.play_button.configure(text="▶")
            self.vlc_player.pause()
            self.base_channel.pause()
            self.voice_channel.pause()

    def start_playback(self):
        if not self.audio_ready:
            self.folder_label.configure(text="No hay salida de audio disponible", text_color="#f07e7e")
            return
        self.stop_playback()
        try:
            media = self.vlc_instance.media_new(str(self.loaded_video))
            self.vlc_player = self.vlc_instance.media_player_new()
            self.vlc_player.set_media(media)
            self.vlc_player.set_hwnd(self.video_label.winfo_id())
            self.vlc_player.audio_set_mute(True)
            self.vlc_player.play()
            self.vlc_player.audio_set_mute(True)
            self.video_fps = 30
            self.video_duration = pygame.mixer.Sound(str(self.loaded_base_audio)).get_length()
            self.timeline.configure(to=max(1, self.video_duration))
            self.base_channel.play(pygame.mixer.Sound(str(self.loaded_base_audio)))
            self.voice_channel.play(pygame.mixer.Sound(str(self.loaded_voice_audio)))
        except (pygame.error, OSError) as error:
            self.stop_playback()
            self.folder_label.configure(text=f"No se pudo reproducir: {error}", text_color="#f07e7e")
            return
        self.video_started_at = time.monotonic()
        self.video_position = 0
        self.timeline.set(0)
        self.update_time_label(0)
        self.display_frame_count = 0
        self.display_fps = 0
        self.voice_channel.set_volume(float(self.voice_volume.get()))
        self.is_paused = False
        self.play_button.configure(text="Ⅱ")
        self.update_video_frame()

    def update_video_frame(self):
        if self.vlc_player is None or self.is_paused:
            return
        elapsed = max(0, self.vlc_player.get_time() / 1000)
        self.video_position = elapsed
        if self.vlc_player.get_state() in (vlc.State.Ended, vlc.State.Error):
            self.stop_playback()
            return
        if not self.seeking:
            self.timeline.set(min(self.video_position, self.video_duration))
            self.update_time_label(self.video_position)
        self.display_frame_count += 1
        elapsed_seconds = time.monotonic() - self.video_started_at
        if elapsed_seconds > 0:
            self.display_fps = self.display_frame_count / elapsed_seconds
        if hasattr(self, "fps_label"):
            self.fps_label.configure(text=f"FPS: {self.display_fps:.1f} / 30")
        self.video_after_id = self.after(1000 // 30, self.update_video_frame)

    def set_voice_volume(self, value):
        percentage = int(float(value) * 100)
        self.volume_value.configure(text=f"{percentage}%")
        if self.voice_channel:
            self.voice_channel.set_volume(float(value))

    def update_time_label(self, position):
        def format_time(value):
            seconds = max(0, int(value))
            return f"{seconds // 60:02d}:{seconds % 60:02d}"

        if hasattr(self, "time_label"):
            self.time_label.configure(text=f"{format_time(position)} / {format_time(self.video_duration)}")

    def preview_timeline(self, value):
        position = float(value)
        self.update_time_label(position)
        if self.vlc_player and self.video_duration:
            self.vlc_player.set_time(int(position * 1000))

    def finish_timeline_seek(self, _event=None):
        self.seek_video(self.timeline.get())

    def seek_video(self, value):
        if not self.vlc_player or not self.video_duration:
            return
        self.seeking = True
        position = float(value)
        was_playing = not self.is_paused
        self.video_position = position
        self.vlc_player.set_time(int(position * 1000))
        self.update_time_label(position)
        if self.video_started_at is not None:
            self.video_started_at = time.monotonic() - position
            self.base_channel.stop()
            self.voice_channel.stop()
            base_sound = self.load_audio_from_position(self.loaded_base_audio, position)
            voice_sound = self.load_audio_from_position(self.loaded_voice_audio, position)
            self.base_channel.play(base_sound)
            self.voice_channel.play(voice_sound)
            self.voice_channel.set_volume(float(self.voice_volume.get()))
            if not was_playing:
                self.base_channel.pause()
                self.voice_channel.pause()
        self.seeking = False

    def load_audio_from_position(self, audio_file, position):
        with wave.open(str(audio_file), "rb") as audio:
            frame_start = min(int(position * audio.getframerate()), audio.getnframes())
            audio.setpos(frame_start)
            audio_data = audio.readframes(audio.getnframes() - frame_start)
        return pygame.mixer.Sound(buffer=audio_data)

    def stop_playback(self):
        if self.video_after_id:
            self.after_cancel(self.video_after_id)
            self.video_after_id = None
        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.release()
            self.vlc_player = None
        self.video_started_at = None
        if self.base_channel:
            self.base_channel.stop()
        if self.voice_channel:
            self.voice_channel.stop()
        if hasattr(self, "play_button"):
            self.play_button.configure(text="▶")
        self.is_paused = False
        self.video_position = 0
        if hasattr(self, "timeline"):
            self.timeline.set(0)
            self.update_time_label(0)

    def close_player_window(self):
        self.stop_playback()
        if self.player_window and self.player_window.winfo_exists():
            self.player_window.destroy()
        self.player_window = None

    def run_pipeline(self, url):
        self.events.put(("status", "Obteniendo titulo del video..."))
        with YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "js_runtimes": {"deno": {"path": str(DENO_FILE)}},
        }) as downloader:
            video_info = downloader.extract_info(url, download=False)
        video_title = safe_folder_name(video_info.get("title", "video"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        conversion_dir = BASE_DIR / "conversiones" / f"{video_title}_{timestamp}"
        conversion_dir.mkdir(parents=True, exist_ok=True)
        video_file = conversion_dir / "video_descargado.mp4"
        audio_file = conversion_dir / "audio_extraido.wav"
        instrumental_file = conversion_dir / "instrumental.wav"
        voice_file = conversion_dir / "voz.wav"
        output_file = conversion_dir / "video_karaoke.mp4"
        steps = [
            ("Descargando video...", "yutu.py", [url, str(conversion_dir)]),
            ("Extrayendo audio...", "extract.py", [str(video_file)]),
            ("Separando voz e instrumental...", "split.py", [str(audio_file)]),
            ("Añadiendo instrumental...", "NewWav.py", [str(video_file), str(instrumental_file)]),
        ]
        try:
            for message, script, arguments in steps:
                self.events.put(("status", message))
                python_executable = (
                    str(SPLITTER_PYTHON)
                    if script == "split.py" and SPLITTER_PYTHON.exists()
                    else sys.executable
                )
                if getattr(sys, "frozen", False):
                    command = [str(runtime_script(script)), *arguments]
                else:
                    command = [python_executable, "-u", str(runtime_script(script)), *arguments]
                print(f"\n--- {message} ({script}) ---", flush=True)
                process = subprocess.Popen(
                    command,
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=0 if SHOW_CONSOLES else subprocess.CREATE_NO_WINDOW,
                )
                position_console(process)
                output_lines = []
                assert process.stdout is not None
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        output_lines.append(line)
                        print(line, flush=True)
                        self.events.put(("log", line))
                process.wait()
                if process.returncode != 0:
                    details = output_lines[-1] if output_lines else "Error desconocido"
                    raise RuntimeError(f"{script}: {details}")
            if not voice_file.exists() or not instrumental_file.exists():
                raise RuntimeError("No se generaron los archivos voz.wav e instrumental.wav.")
            self.events.put(("success", "Listo"))
        except Exception as error:
            self.events.put(("error", str(error)))

    def process_events(self):
        try:
            while True:
                event, message = self.events.get_nowait()
                if event == "status":
                    self.status_label.configure(text=message, text_color="#a9b8c0")
                elif event == "log":
                    self.status_label.configure(text=message[:140], text_color="#a9b8c0")
                elif event == "success":
                    self.status_label.configure(text=message, text_color="#72d6c9")
                    self.finish_conversion()
                else:
                    details = message.replace("\r", "").splitlines()
                    visible_error = details[-1] if details else message
                    self.status_label.configure(text="Error: " + visible_error[:140], text_color="#f07e7e")
                    self.finish_conversion()
        except queue.Empty:
            pass
        self.after(100, self.process_events)

    def finish_conversion(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.convert_button.configure(state="normal", text="Convertir")
        self.url_input.configure(state="normal")


if __name__ == "__main__":
    app = KaraokeApp()
    app.mainloop()
