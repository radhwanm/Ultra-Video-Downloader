import os
import queue
import shutil
import threading
import tkinter.filedialog as filedialog

import customtkinter as ctk
import yt_dlp

try:
    from plyer import notification
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class UltraDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ultra Video Downloader PRO")
        self.geometry("1120x920")
        self.resizable(False, False)
        self.configure(fg_color="#f5f5f7")
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.download_queue = queue.Queue()
        self.is_downloading = False
        self.failed_downloads = 0
        self.embed_thumbnail_var = ctk.BooleanVar(value=True)
        self.audio_quality_options = [128, 192, 256, 320]
        self.audio_quality_var = ctk.IntVar(value=192)
        self.ffmpeg_path = self.detect_ffmpeg()
        self.create_widgets()

    def detect_ffmpeg(self):
        system_path = shutil.which("ffmpeg")
        if system_path:
            return os.path.dirname(system_path)

        current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        ffmpeg_binary = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

        if os.path.exists(os.path.join(current_dir, ffmpeg_binary)):
            return current_dir

        local_ffmpeg_dir = os.path.join(current_dir, "ffmpeg")
        if os.path.exists(os.path.join(local_ffmpeg_dir, ffmpeg_binary)):
            return local_ffmpeg_dir

        return None

    def show_notification(self, title, message):
        if NOTIFICATION_AVAILABLE:
            try:
                notification.notify(title=title, message=message, timeout=5, app_name="Ultra Downloader")
            except Exception:
                pass

    def safe_ui_update(self, widget_command, *args, **kwargs):
        self.after(0, lambda: widget_command(*args, **kwargs))

    def log(self, text):
        def insert_log():
            self.log_box.insert("end", f"⚡ {text}\n")
            self.log_box.see("end")
            try:
                total_lines = int(self.log_box.index("end-1c").split(".")[0])
                if total_lines > 500:
                    self.log_box.delete("1.0", "100.0")
            except Exception:
                pass

        self.safe_ui_update(insert_log)

    def update_queue_count(self, count=None):
        if count is None:
            count = self.download_queue.qsize()
        self.safe_ui_update(
            self.queue_count_label.configure,
            text=f"📊 الروابط المتبقية في الانتظار: {count}",
        )

    def update_audio_quality_label(self, value):
        quality_index = int(float(value))
        quality_kbps = self.audio_quality_options[quality_index]
        self.audio_quality_var.set(quality_kbps)
        self.audio_quality_value_label.configure(text=f"{quality_kbps} kbps")

    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=26, pady=22)

        title_frame = ctk.CTkFrame(self.main_frame, corner_radius=28, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        title_frame.pack(padx=8, pady=(0, 16), fill="x")
        title_label = ctk.CTkLabel(
            title_frame,
            text="Ultra Video Downloader PRO",
            font=("SF Pro Display", 32, "bold"),
            text_color="#111111",
        )
        title_label.pack(pady=(18, 4))
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Clean downloads for video, audio, and playlists",
            font=("SF Pro Text", 15),
            text_color="#6e6e73",
        )
        subtitle_label.pack(pady=(0, 18))

        self.url_entry = ctk.CTkEntry(
            self.main_frame,
            placeholder_text="ألصق رابط الفيديو أو قائمة التشغيل هنا...",
            width=950,
            height=50,
            font=("SF Pro Text", 15),
            corner_radius=18,
            fg_color="#ffffff",
            text_color="#111111",
            placeholder_text_color="#8e8e93",
            border_color="#d2d2d7",
            border_width=1,
        )
        self.url_entry.pack(pady=(0, 14), padx=8, fill="x")

        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 14))

        self.fetch_btn = ctk.CTkButton(
            btn_frame,
            text="جلب المعلومات",
            width=220,
            height=46,
            font=("SF Pro Text", 14, "bold"),
            command=self.start_fetch_thread,
            corner_radius=22,
            fg_color="#ffffff",
            hover_color="#f2f2f7",
            text_color="#111111",
            border_width=1,
            border_color="#d2d2d7",
        )
        self.fetch_btn.grid(row=0, column=0, padx=10)

        self.add_btn = ctk.CTkButton(
            btn_frame,
            text="إضافة للطابور",
            width=220,
            height=46,
            fg_color="#e8f0ff",
            hover_color="#dce8ff",
            text_color="#175cd3",
            font=("SF Pro Text", 14, "bold"),
            command=self.add_to_queue,
            corner_radius=22,
        )
        self.add_btn.grid(row=0, column=1, padx=10)

        self.download_btn = ctk.CTkButton(
            btn_frame,
            text="بدء التنزيل",
            width=220,
            height=46,
            fg_color="#0071e3",
            hover_color="#0062c3",
            font=("SF Pro Text", 14, "bold"),
            command=self.start_queue,
            corner_radius=22,
        )
        self.download_btn.grid(row=0, column=2, padx=10)

        info_frame = ctk.CTkFrame(self.main_frame, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        info_frame.pack(pady=(0, 14), padx=8, fill="x")
        info_title = ctk.CTkLabel(
            info_frame,
            text="تفاصيل الفيديو",
            font=("SF Pro Display", 17, "bold"),
            text_color="#111111",
        )
        info_title.pack(pady=(14, 4))

        self.video_info = ctk.CTkTextbox(
            info_frame,
            width=950,
            height=120,
            font=("SF Pro Text", 14),
            corner_radius=16,
            fg_color="#f5f5f7",
            text_color="#1d1d1f",
            border_width=0,
        )
        self.video_info.pack(pady=(4, 14), padx=14)

        options_frame = ctk.CTkFrame(self.main_frame, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        options_frame.pack(pady=(0, 12), padx=8, fill="x")
        options_title = ctk.CTkLabel(
            options_frame,
            text="خيارات التنزيل",
            font=("SF Pro Display", 17, "bold"),
            text_color="#111111",
        )
        options_title.grid(row=0, column=0, columnspan=2, pady=(14, 6))

        qualities = ["أفضل جودة", "1080p", "720p", "480p", "360p", "MP3 صوت فقط"]
        self.quality_menu = ctk.CTkOptionMenu(
            options_frame,
            values=qualities,
            width=240,
            height=40,
            command=self.on_quality_change,
            corner_radius=18,
            fg_color="#f5f5f7",
            button_color="#f5f5f7",
            button_hover_color="#ebebf0",
            text_color="#111111",
            dropdown_fg_color="#ffffff",
            dropdown_text_color="#111111",
            dropdown_hover_color="#f2f2f7",
        )
        self.quality_menu.set("أفضل جودة")
        self.quality_menu.grid(row=1, column=0, padx=40, pady=(4, 16))

        self.format_menu = ctk.CTkOptionMenu(
            options_frame,
            values=["mp4", "mkv", "webm", "mp3"],
            width=200,
            height=40,
            corner_radius=18,
            fg_color="#f5f5f7",
            button_color="#f5f5f7",
            button_hover_color="#ebebf0",
            text_color="#111111",
            dropdown_fg_color="#ffffff",
            dropdown_text_color="#111111",
            dropdown_hover_color="#f2f2f7",
        )
        self.format_menu.set("mp4")
        self.format_menu.grid(row=1, column=1, padx=40, pady=(4, 16))

        self.playlist_var = ctk.BooleanVar(value=False)
        self.playlist_checkbox = ctk.CTkCheckBox(
            self.main_frame,
            text="تفعيل تحميل قوائم التشغيل (Playlist)",
            variable=self.playlist_var,
            font=("SF Pro Text", 14, "bold"),
            text_color="#1d1d1f",
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=7,
            fg_color="#0071e3",
            hover_color="#0062c3",
            border_color="#c7c7cc",
        )
        self.playlist_checkbox.pack(pady=(0, 12), padx=12, anchor="e")

        settings_frame = ctk.CTkFrame(self.main_frame, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        settings_frame.pack(pady=(0, 12), padx=8, fill="x")
        settings_title = ctk.CTkLabel(settings_frame, text="الإعدادات", font=("SF Pro Display", 17, "bold"), text_color="#111111")
        settings_title.pack(pady=(10, 4))

        self.embed_thumbnail_checkbox = ctk.CTkCheckBox(
            settings_frame,
            text="تضمين صورة الألبوم داخل ملف MP3",
            variable=self.embed_thumbnail_var,
            font=("SF Pro Text", 13, "bold"),
            text_color="#1d1d1f",
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=7,
            fg_color="#0071e3",
            hover_color="#0062c3",
            border_color="#c7c7cc",
        )
        self.embed_thumbnail_checkbox.pack(pady=(0, 10), padx=16, anchor="e")

        audio_quality_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        audio_quality_row.pack(padx=16, pady=(0, 12), fill="x")

        self.audio_quality_value_label = ctk.CTkLabel(
            audio_quality_row,
            text=f"{self.audio_quality_var.get()} kbps",
            font=("SF Pro Text", 13, "bold"),
            text_color="#0071e3",
            width=90,
        )
        self.audio_quality_value_label.pack(side="left", padx=(0, 12))

        self.audio_quality_slider = ctk.CTkSlider(
            audio_quality_row,
            from_=0,
            to=len(self.audio_quality_options) - 1,
            number_of_steps=len(self.audio_quality_options) - 1,
            command=self.update_audio_quality_label,
            progress_color="#0071e3",
            button_color="#ffffff",
            button_hover_color="#f2f2f7",
            fg_color="#d2d2d7",
        )
        self.audio_quality_slider.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.audio_quality_slider.set(1)

        self.audio_quality_label = ctk.CTkLabel(
            audio_quality_row,
            text="جودة الصوت",
            font=("SF Pro Text", 13, "bold"),
            text_color="#1d1d1f",
        )
        self.audio_quality_label.pack(side="right")

        if not self.ffmpeg_path:
            self.embed_thumbnail_var.set(False)
            self.embed_thumbnail_checkbox.configure(state="disabled")

        path_frame = ctk.CTkFrame(self.main_frame, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        path_frame.pack(pady=(0, 12), padx=8, fill="x")
        self.path_label = ctk.CTkLabel(
            path_frame,
            text=f"📂 {self.download_path}",
            wraplength=700,
            font=("SF Pro Text", 13),
            text_color="#6e6e73",
        )
        self.path_label.pack(side="right", padx=20, pady=12)

        path_btn = ctk.CTkButton(
            path_frame,
            text="تغيير مجلد الحفظ",
            width=170,
            height=38,
            command=self.choose_folder,
            corner_radius=18,
            fg_color="#f5f5f7",
            hover_color="#ebebf0",
            text_color="#111111",
            border_width=1,
            border_color="#d2d2d7",
            font=("SF Pro Text", 13, "bold"),
        )
        path_btn.pack(side="left", padx=20)

        progress_frame = ctk.CTkFrame(self.main_frame, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        progress_frame.pack(pady=(0, 12), padx=8, fill="x")
        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=800, height=15)
        self.progress_bar.pack(side="left", padx=16, pady=16)
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#34c759", fg_color="#e5e5ea", corner_radius=10)
        self.progress_label = ctk.CTkLabel(progress_frame, text="0%", font=("SF Pro Text", 14, "bold"), width=80, text_color="#1d1d1f")
        self.progress_label.pack(side="right", padx=16)

        self.queue_count_label = ctk.CTkLabel(
            self.main_frame,
            text="📊 الروابط المتبقية في الانتظار: 0",
            font=("SF Pro Text", 14, "bold"),
            text_color="#0071e3",
        )
        self.queue_count_label.pack(pady=(0, 12))

        log_frame = ctk.CTkFrame(self.main_frame, corner_radius=24, fg_color="#ffffff", border_width=1, border_color="#e5e5ea")
        log_frame.pack(pady=(0, 12), padx=8, fill="both", expand=True)
        log_title = ctk.CTkLabel(log_frame, text="سجل العمليات", font=("SF Pro Display", 17, "bold"), text_color="#111111")
        log_title.pack(pady=(14, 4))
        self.log_box = ctk.CTkTextbox(
            log_frame,
            font=("SF Mono", 12),
            fg_color="#f5f5f7",
            text_color="#1d1d1f",
            corner_radius=16,
            border_width=0,
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(4, 14))

        ffmpeg_text = (
            "✅ نظام دمج الفيديوهات FFmpeg: نشط وجاهز"
            if self.ffmpeg_path
            else "⚠️ تحذير: أداة FFmpeg مفقودة (تضمين صورة الغلاف وجودات 1080p+ يتطلبها)"
        )
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text=ffmpeg_text,
            font=("SF Pro Text", 12),
            text_color="#6e6e73",
        )
        self.status_label.pack(pady=(0, 4))

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path = folder
            self.path_label.configure(text=f"📂 {self.download_path}")

    def on_quality_change(self, value):
        if value == "MP3 صوت فقط":
            self.format_menu.set("mp3")
        elif self.format_menu.get() == "mp3":
            self.format_menu.set("mp4")

    def start_fetch_thread(self):
        url = self.url_entry.get().strip()
        download_playlist = self.playlist_var.get()
        if not url:
            self.log("خطأ: يرجى إدخال الرابط أولاً ليتم جلبه.")
            return

        threading.Thread(target=self.fetch_video_info, args=(url, download_playlist), daemon=True).start()

    def fetch_video_info(self, url, download_playlist):
        self.log("جاري استخراج بيانات ومعلومات الرابط...")
        ydl_opts = {"noplaylist": not download_playlist, "quiet": True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "عنوان غير متاح")
                uploader = info.get("uploader", "قناة غير معروفة")
                duration_seconds = info.get("duration", 0) or 0
                minutes = duration_seconds // 60
                seconds = duration_seconds % 60
                info_text = f"📌 العنوان: {title}\n📺 الناشر: {uploader}\n⏱️ المدة: {minutes} دقيقة و {seconds} ثانية"
                self.safe_ui_update(self.video_info.delete, "1.0", "end")
                self.safe_ui_update(self.video_info.insert, "end", info_text)
                self.log("تم استخراج وعرض تفاصيل الرابط بنجاح.")
        except Exception as e:
            self.log(f"فشل استخراج البيانات: {str(e)}")

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if url:
            self.download_queue.put(url)
            self.log("تمت إضافة الرابط بنجاح إلى الطابور.")
            self.update_queue_count()
            self.url_entry.delete(0, "end")
        else:
            self.log("تنبيه: لا يوجد رابط مكتوب لإضافته إلى الطابور.")

    def start_queue(self):
        if self.is_downloading:
            self.log("عملية التحميل قيد التنفيذ والعمل حالياً بالفعل!")
            return
        if self.download_queue.empty():
            self.log("الطابور فارغ تماماً، يرجى إضافة روابط أولاً.")
            return

        self.is_downloading = True
        self.failed_downloads = 0
        download_options = {
            "quality": self.quality_menu.get(),
            "format": self.format_menu.get(),
            "download_playlist": self.playlist_var.get(),
            "embed_thumbnail": self.embed_thumbnail_var.get(),
            "audio_quality": str(self.audio_quality_var.get()),
        }
        threading.Thread(target=self.process_queue, args=(download_options,), daemon=True).start()

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded_bytes = d.get("downloaded_bytes", 0)
            if total_bytes:
                percentage = downloaded_bytes / total_bytes
                self.safe_ui_update(self.progress_bar.set, percentage)
                self.safe_ui_update(self.progress_label.configure, text=f"{int(percentage * 100)}%")

    def process_queue(self, download_options):
        while not self.download_queue.empty():
            pending_before_get = self.download_queue.qsize()
            self.update_queue_count(pending_before_get)

            url = self.download_queue.get()
            self.log(f"بدء معالجة وتحميل الرابط: {url}")
            self.safe_ui_update(self.progress_bar.set, 0)
            self.safe_ui_update(self.progress_label.configure, text="0%")

            quality = download_options["quality"]
            fmt = download_options["format"]
            ydl_opts = {
                "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
                "ffmpeg_location": self.ffmpeg_path,
                "noplaylist": not download_options["download_playlist"],
                "progress_hooks": [self.progress_hook],
            }

            if quality == "MP3 صوت فقط" or fmt == "mp3":
                ydl_opts.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": download_options["audio_quality"],
                            },
                        ],
                    }
                )
                if download_options["embed_thumbnail"] and self.ffmpeg_path:
                    ydl_opts["writethumbnail"] = True
                    ydl_opts["postprocessors"].append({"key": "EmbedThumbnail"})
            else:
                res_map = {"1080p": "1080", "720p": "720", "480p": "480", "360p": "360"}
                res = res_map.get(quality)
                if res:
                    ydl_opts["format"] = f"bestvideo[height<={res}]+bestaudio/best"
                else:
                    ydl_opts["format"] = "bestvideo+bestaudio/best"
                ydl_opts["merge_output_format"] = fmt

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self.log("اكتمل تحميل الملف وحفظه بنجاح!")
                self.show_notification("Ultra Downloader", "تم إنهاء تحميل الملف بنجاح!")
            except Exception as e:
                self.failed_downloads += 1
                self.log(f"توقف التحميل بسبب خطأ بالرابط: {str(e)}")
                self.show_notification("Ultra Downloader", f"فشل تحميل الرابط.\nالخطأ: {str(e)}")
            finally:
                self.download_queue.task_done()
                self.update_queue_count()

        self.is_downloading = False
        self.update_queue_count(0)
        if self.failed_downloads:
            self.log(f"⚠️ انتهت معالجة الطابور مع {self.failed_downloads} عملية فاشلة.")
        else:
            self.log("✨ تمت معالجة وتنزيل جميع المهام المتواجدة في طابور التحميل بنجاح.")


if __name__ == "__main__":
    app = UltraDownloader()
    app.mainloop()
