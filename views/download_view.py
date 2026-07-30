import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import os
import sys
import subprocess
import re
import requests
import zipfile
import io
import datetime

class PlaylistDialog(ctk.CTkToplevel):
    def __init__(self, master, entries, **kwargs):
        super().__init__(master, **kwargs)
        self.title("選擇要下載的影片")
        self.geometry("750x650")
        
        self.master_view = master 
        self.entries = entries
        
        self.page_size = 50
        self.current_page = 0
        self.total_pages = (len(entries) + self.page_size - 1) // self.page_size
        
        # Initialize selection state (Default to False)
        self.selected_state = {}
        for entry in entries:
            if isinstance(entry, dict):
                url = entry.get('url') or entry.get('id', '')
                if url and not url.startswith('http'):
                     url = f"https://www.youtube.com/watch?v={url}"
                if url:
                    self.selected_state[url] = False
            
        self.setup_ui()
        self.load_page()
        
        # Center Window relative to parent
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        
        # Get parent center
        p_width = parent.winfo_width()
        p_height = parent.winfo_height()
        p_x = parent.winfo_x()
        p_y = parent.winfo_y()
        
        # Dialog Dimensions
        d_width = 750
        d_height = 650
        
        x = p_x + (p_width // 2) - (d_width // 2)
        y = p_y + (p_height // 2) - (d_height // 2)
        
        # Fallback to screen center if parent size isn't loaded yet
        if p_width <= 1 or p_height <= 1:
            s_width = self.winfo_screenwidth()
            s_height = self.winfo_screenheight()
            x = (s_width // 2) - (d_width // 2)
            y = (s_height // 2) - (d_height // 2)
            
        self.geometry(f"{d_width}x{d_height}+{max(0, x)}+{max(0, y)}")
        self.transient(master.winfo_toplevel())
        self.grab_set()

    def setup_ui(self):
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text=f"發現 {len(self.entries)} 部影片，請勾選要下載的項目：", font=("Microsoft JhengHei UI", 16, "bold"))
        self.title_lbl.pack(side="left")
        
        # Controls Frame for Bulk Selections
        self.controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.controls_frame.pack(side="right")
        
        btn_font = ("Microsoft JhengHei UI", 13)
        
        ctk.CTkButton(self.controls_frame, text="全選此頁", width=85, height=28, font=btn_font, fg_color="#00897B", hover_color="#00695C", command=self.select_all_page).pack(side="left", padx=3)
        ctk.CTkButton(self.controls_frame, text="取消此頁", width=85, height=28, font=btn_font, fg_color="#D32F2F", hover_color="#B71C1C", command=self.deselect_all_page).pack(side="left", padx=3)
        
        ctk.CTkLabel(self.controls_frame, text="|", font=("Microsoft JhengHei UI", 16)).pack(side="left", padx=5)
        
        ctk.CTkButton(self.controls_frame, text="全選所有", width=85, height=28, font=btn_font, fg_color="#00897B", hover_color="#00695C", command=self.select_all_global).pack(side="left", padx=3)
        ctk.CTkButton(self.controls_frame, text="取消所有", width=85, height=28, font=btn_font, fg_color="#D32F2F", hover_color="#B71C1C", command=self.deselect_all_global).pack(side="left", padx=3)
        
        # Scrollable Frame for items
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=700, height=420)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Footer Pagination
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.pack(fill="x", padx=20, pady=5)
        
        self.prev_btn = ctk.CTkButton(self.pagination_frame, text="上一頁", width=80, command=self.prev_page)
        self.prev_btn.pack(side="left")
        
        self.page_lbl = ctk.CTkLabel(self.pagination_frame, text=f"第 1 / {self.total_pages} 頁", font=("Microsoft JhengHei UI", 14))
        self.page_lbl.pack(side="left", fill="x", expand=True)
        
        self.next_btn = ctk.CTkButton(self.pagination_frame, text="下一頁", width=80, command=self.next_page)
        self.next_btn.pack(side="right")
        
        # Confirm Buttons
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(pady=(5, 15))
        
        self.confirm_btn = ctk.CTkButton(self.footer_frame, text="開始下載勾選項目", font=("Microsoft JhengHei UI", 15, "bold"), fg_color="#E91E63", hover_color="#C2185B", command=self.on_confirm_click)
        self.confirm_btn.pack(side="left", padx=10)
        
        self.cancel_btn = ctk.CTkButton(self.footer_frame, text="取消", font=("Microsoft JhengHei UI", 15), fg_color="gray", command=self.on_cancel_click)
        self.cancel_btn.pack(side="left", padx=10)

    def load_page(self):
        # Clear frame
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        self.page_lbl.configure(text=f"第 {self.current_page + 1} / {self.total_pages} 頁")
        self.prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
        
        # Selection state is managed via buttons now
        
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.entries))
        
        # Create Checkboxes for this page
        for i in range(start_idx, end_idx):
            entry = self.entries[i]
            if not isinstance(entry, dict):
                continue
            title = entry.get('title', 'Unknown')
            url = entry.get('url') or entry.get('id', '')
            if url and not url.startswith('http'):
                 url = f"https://www.youtube.com/watch?v={url}"
                 
            duration = entry.get('duration')
            dur_str = f"({int(duration//60):02d}:{int(duration%60):02d})" if duration else ""
            
            # Setup Var with current state from dict
            is_selected = self.selected_state.get(url, False)
            var = ctk.BooleanVar(value=is_selected)
            
            # Bind command to update dict
            def make_cmd(u=url, v=var):
                return lambda: self.update_selection(u, v.get())
                
            chk = ctk.CTkCheckBox(
                self.scroll_frame, 
                text=f"{i+1}. {title} {dur_str}", 
                variable=var, 
                command=make_cmd(url, var),
                font=("Microsoft JhengHei UI", 14)
            )
            chk.pack(anchor="w", pady=5, padx=5)

    def update_selection(self, url, value):
        self.selected_state[url] = value

    def select_all_page(self):
        self._set_page_selection(True)
        self.load_page()
        
    def deselect_all_page(self):
        self._set_page_selection(False)
        self.load_page()
        
    def _set_page_selection(self, state):
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.entries))
        for i in range(start_idx, end_idx):
            entry = self.entries[i]
            url = entry.get('url', '')
            if url and not url.startswith('http'):
                 url = f"https://www.youtube.com/watch?v={url}"
            self.selected_state[url] = state

    def select_all_global(self):
        self._set_global_selection(True)
        self.load_page()
        
    def deselect_all_global(self):
        self._set_global_selection(False)
        self.load_page()
        
    def _set_global_selection(self, state):
        for url in self.selected_state:
            self.selected_state[url] = state

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()
            
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_page()

    def on_confirm_click(self):
        selected_urls = [url for url, is_sel in self.selected_state.items() if is_sel]
        self.destroy()
        if not selected_urls:
            self.master_view.log("未選擇任何影片，取消下載。")
            self.master_view.stop_download()
            return
            
        self.master_view.log(f"確認加入 {len(selected_urls)} 部影片至下載佇列。")
        self.master_view.status_label.configure(text="準備開始下載...", font=("Microsoft JhengHei UI", 15, "bold"))
        import threading
        threading.Thread(target=self.master_view.run_download_task, args=(selected_urls,), daemon=True).start()
        
    def on_cancel_click(self):
        self.master_view.log("取消播放清單下載。")
        self.destroy()
        self.master_view.stop_download()

class DownloadView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Paths
        if getattr(sys, 'frozen', False):
            self.script_dir = os.path.dirname(sys.executable)
        else:
            self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

        self.tools_dir = os.path.join(self.script_dir, "tools")
        if not os.path.exists(self.tools_dir):
            try:
                os.makedirs(self.tools_dir, exist_ok=True)
            except Exception:
                pass

        self.output_dir = os.path.join(self.script_dir, "Outputs", "Downloads")
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception:
                pass

        self.yt_dlp_path = self.get_tool_path("yt-dlp.exe")
        self.deno_path = self.get_tool_path("deno.exe")
        self.threads_config_path = os.path.join(self.tools_dir, "threads_config.json")

        # State
        self.is_downloading = False
        self.current_process = None
        self.core_checked = False # Flag to avoid re-checking every time
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Log area (Row 3) expands

        self.setup_ui()
        self.log("系統初始化完成... (等待任務)")

    def setup_ui(self):
        # --- Input Section (Row 0) ---
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, pady=(10, 5), padx=20, sticky="ew")
        
        self.url_instruction_label = ctk.CTkLabel(
            self.input_frame,
            text="貼上影片網址(可多筆，每行一個網址)：",
            font=("Microsoft JhengHei UI", 15, "bold"),
            text_color="white"
        )
        self.url_instruction_label.pack(side="top", anchor="w", padx=(0, 15), pady=(0, 5))
        
        self.url_entry = ctk.CTkTextbox(
            self.input_frame,
            height=120,
            font=("Microsoft JhengHei UI", 15),
            fg_color="#2B2B2B", # Matches the file list box color in subtitle view
            text_color="#e0e0e0" # Light text against dark bg
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))

        # --- [NEW] Right-Click Context Menu for URL Textbox ---
        self.url_context_menu = tk.Menu(self, tearoff=0, font=("Microsoft JhengHei UI", 13), bg="#333333", fg="white", activebackground="#00897B")
        self.url_context_menu.add_command(label="複製 (Copy)", command=lambda: self.url_entry._textbox.event_generate("<<Copy>>"))
        self.url_context_menu.add_command(label="貼上 (Paste)", command=lambda: self.url_entry._textbox.event_generate("<<Paste>>"))
        self.url_context_menu.add_separator()
        self.url_context_menu.add_command(label="全選 (Select All)", command=lambda: self.url_entry._textbox.tag_add("sel", "1.0", "end"))
        
        def show_url_context_menu(event):
            self.url_context_menu.tk_popup(event.x_root, event.y_root)
            
        self.url_entry.bind("<Button-3>", show_url_context_menu)
        # --------------------------------------------------------

        self.download_btn = ctk.CTkButton(
            self.input_frame,
            text="開始下載",
            height=40,
            width=120,
            fg_color="#E91E63", # Unify Start Button Color
            text_color="white",
            hover_color="#C2185B",
            font=("Microsoft JhengHei UI", 15, "bold"),
            command=self.start_download_thread
        )
        self.download_btn.pack(side="right")
        
        # Auto-focus when this tab is selected
        self.bind("<Visibility>", lambda e: self.url_entry.focus_set())

        # --- Options Section (Row 1) ---
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=1, column=0, pady=(5, 5), padx=20, sticky="ew")

        # Checkbox for Split Chapters
        self.split_chapters_var = ctk.BooleanVar(value=False)
        self.split_chapters_chk = ctk.CTkCheckBox(
            self.options_frame, 
            text="按章節自動分割", 
            variable=self.split_chapters_var,
            font=("Microsoft JhengHei UI", 15),
            command=self.on_split_chapters_toggle
        )
        self.split_chapters_chk.pack(side="left", padx=(0, 15))

        # Checkbox for Download Subtitles
        self.dl_subs_var = ctk.BooleanVar(value=False)
        self.dl_subs_chk = ctk.CTkCheckBox(
            self.options_frame, 
            text="附加下載字幕 (SRT)", 
            variable=self.dl_subs_var,
            font=("Microsoft JhengHei UI", 15)
        )
        self.dl_subs_chk.pack(side="left", padx=(0, 5))
        
        self.subs_lang_var = ctk.StringVar(value="自動判定")
        self.subs_lang_menu = ctk.CTkComboBox(
            self.options_frame,
            values=["繁體中文", "簡體中文", "英文", "日文", "自動判定"],
            variable=self.subs_lang_var,
            width=100, height=30,
            font=("Microsoft JhengHei UI", 14),
            dropdown_font=("Microsoft JhengHei UI", 14)
        )
        self.subs_lang_menu.pack(side="left", padx=(0, 15))

        # Quality Selection
        self.quality_var = ctk.StringVar(value="最佳畫質 (Auto)")
        self.quality_menu = ctk.CTkComboBox(
            self.options_frame,
            values=["最佳畫質 (Auto)", "2160p (4K)", "1440p (2K)", "1080p (FHD)", "720p (HD)", "480p"],
            variable=self.quality_var,
            width=180, height=30, # Increased width from 140
            font=("Microsoft JhengHei UI", 15),
            dropdown_font=("Microsoft JhengHei UI", 15)
        )
        self.quality_menu.pack(side="left", padx=(0, 15))

        # Format Selection
        self.format_var = ctk.StringVar(value="MP4")
        self.format_menu = ctk.CTkComboBox(
            self.options_frame,
            values=["MP4", "MP3", "WAV", "WMV", "MKV", "MOV"],
            variable=self.format_var,
            width=100, height=30,
            font=("Microsoft JhengHei UI", 15),
            dropdown_font=("Microsoft JhengHei UI", 15)
        )
        self.format_menu.pack(side="left", padx=(0, 15))
        
        # Stop Button
        self.stop_btn = ctk.CTkButton(
            self.options_frame,
            text="中斷",
            width=100,
            height=30,
            fg_color="#D32F2F", # Red
            hover_color="#B71C1C",
            font=("Microsoft JhengHei UI", 15, "bold"),
            command=self.stop_download,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 15))

        # --- [NEW] Range Section (Row 2) ---
        self.range_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.range_frame.grid(row=2, column=0, pady=(5, 5), padx=20, sticky="ew")

        # Checkbox for Clip Video
        self.clip_video_var = ctk.BooleanVar(value=False)
        self.clip_video_chk = ctk.CTkCheckBox(
            self.range_frame, 
            text="下載指定時間片段", 
            variable=self.clip_video_var,
            font=("Microsoft JhengHei UI", 15),
            command=self.on_clip_video_toggle
        )
        self.clip_video_chk.pack(side="left", padx=(0, 15))
        
        self.start_label = ctk.CTkLabel(self.range_frame, text="開始時間:", font=("Microsoft JhengHei UI", 15))
        self.start_label.pack(side="left", padx=(0, 5))
        
        self.start_time_entry = ctk.CTkEntry(
            self.range_frame,
            placeholder_text="00:00:00",
            width=100, height=30,
            font=("Microsoft JhengHei UI", 14),
            state="disabled"
        )
        self.start_time_entry.pack(side="left", padx=(0, 15))
        
        self.end_label = ctk.CTkLabel(self.range_frame, text="結束時間:", font=("Microsoft JhengHei UI", 15))
        self.end_label.pack(side="left", padx=(0, 5))
        
        self.end_time_entry = ctk.CTkEntry(
            self.range_frame,
            placeholder_text="00:10:00",
            width=100, height=30,
            font=("Microsoft JhengHei UI", 14),
            state="disabled"
        )
        self.end_time_entry.pack(side="left", padx=(0, 15))


        self.range_info_label = ctk.CTkLabel(
            self.range_frame,
            text="(格式: hh:mm:ss、mm:ss 或純秒數)",
            font=("Microsoft JhengHei UI", 13),
            text_color="gray"
        )
        self.range_info_label.pack(side="left")

        # --- Progress & Log Section (Row 3) ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=3, column=0, pady=(0, 5), padx=20, sticky="nsew")
        self.bottom_frame.grid_rowconfigure(2, weight=1) # Log box takes all remaining vertical space
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        
        # --- [NEW] Status Layout (Thumbnail + Progress) ---
        self.status_frame = ctk.CTkFrame(self.bottom_frame, fg_color="#1E1E1E") # Slightly different bg to stand out
        self.status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        self.status_frame.grid_columnconfigure(1, weight=1) # Right side expands
        
        # Left: Thumbnail Canvas (16:9 approx)
        self.thumbnail_canvas = tk.Canvas(self.status_frame, width=240, height=135, bg="#000000", highlightthickness=0)
        self.thumbnail_canvas.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        # Dummy Image / Placeholder
        from PIL import Image, ImageDraw, ImageTk
        img = Image.new("RGB", (240, 135), (40, 40, 40))
        d = ImageDraw.Draw(img)
        d.text((85, 60), "No Image", fill=(150,150,150))
        self.default_thumb = ImageTk.PhotoImage(img)
        self.thumbnail_canvas.create_image(0, 0, image=self.default_thumb, anchor="nw")
        
        # Right Top: Status & Details
        info_frame1 = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        info_frame1.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(info_frame1, text="準備就緒", font=("Microsoft JhengHei UI", 16, "bold"), text_color="#ffa000", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)
        
        # Details inside info_frame1 next to status
        self.speed_label = ctk.CTkLabel(info_frame1, text="速度: -- MiB/s", font=("Microsoft JhengHei UI", 13), text_color="white")
        self.speed_label.pack(side="left", padx=(0, 15))
        
        self.eta_label = ctk.CTkLabel(info_frame1, text="預計: --:--", font=("Microsoft JhengHei UI", 13), text_color="white")
        self.eta_label.pack(side="left", padx=(0, 15))
        
        self.size_label = ctk.CTkLabel(info_frame1, text="大小: -- MiB", font=("Microsoft JhengHei UI", 13), text_color="white")
        self.size_label.pack(side="left", padx=(0, 15))
        
        self.percent_label = ctk.CTkLabel(info_frame1, text="0%", font=("Microsoft JhengHei UI", 16, "bold"), text_color="#ffa000")
        self.percent_label.pack(side="right")
        
        # Right Middle: Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, height=12, progress_color="#ffa000")
        self.progress_bar.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(5, 10))
        self.progress_bar.set(0)
        # ----------------------------------------------------

        # Log
        self.log_box = ctk.CTkTextbox(self.bottom_frame, font=("Microsoft JhengHei UI", 14), fg_color="#000000") # Pure black log background
        self.log_box.grid(row=2, column=0, columnspan=2, sticky="nsew") # Span 2 columns to make room for buttons
        self.log_box.configure(state="disabled")
        
        # Frame for bottom buttons
        self.bottom_btns_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.bottom_btns_frame.grid(row=3, column=0, columnspan=2, pady=(5, 0), sticky="e")
        
        # Moved Update Button
        self.update_btn = ctk.CTkButton(
            self.bottom_btns_frame,
            text="更新核心",
            width=120,
            text_color="white",
            font=("Microsoft JhengHei UI", 15),
            command=self.start_update_thread
        )
        self.update_btn.pack(side="left", padx=(0, 15))
        
        self.open_folder_btn = ctk.CTkButton(self.bottom_btns_frame, text="開啟輸出資料夾", font=("Microsoft JhengHei UI", 15), command=self.open_download_folder, fg_color="#4CAF50", hover_color="#388E3C", text_color="white")
        self.open_folder_btn.pack(side="left")

    def on_split_chapters_toggle(self):
        if self.split_chapters_var.get():
            self.clip_video_var.set(False)
            self.clip_video_chk.configure(state="disabled")
            self.start_time_entry.configure(state="disabled")
            self.end_time_entry.configure(state="disabled")
        else:
            self.clip_video_chk.configure(state="normal")
            if self.clip_video_var.get():
                self.start_time_entry.configure(state="normal")
                self.end_time_entry.configure(state="normal")

    def on_clip_video_toggle(self):
        if self.clip_video_var.get():
            self.split_chapters_var.set(False)
            self.split_chapters_chk.configure(state="disabled")
            self.start_time_entry.configure(state="normal")
            self.end_time_entry.configure(state="normal")
        else:
            self.split_chapters_chk.configure(state="normal")
            self.start_time_entry.configure(state="disabled")
            self.end_time_entry.configure(state="disabled")

    # --- Event Handlers ---
    def on_enter(self):
        """Called when user switches to this view"""
        if not self.core_checked:
            self.core_checked = True # Only check once per session to avoid annoying loops, or maybe checking every time is safer? 
            # Let's check every time but only auto download if missing.
            # If exists, it's quick.
            self.after(500, self.check_core_status)

    # --- Utilities ---
    def log(self, message):
        self.after(0, self._log_safe, message)

    def _log_safe(self, message):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{timestamp} {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def get_tool_path(self, tool_filename):
        candidates = [
            os.path.join(self.tools_dir, tool_filename),
        ]
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', '')
            if meipass:
                candidates.append(os.path.join(meipass, "tools", tool_filename))
                candidates.append(os.path.join(meipass, tool_filename))
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "tools", tool_filename))
            candidates.append(os.path.join(exe_dir, tool_filename))
        
        for p in candidates:
            if os.path.exists(p):
                return p
        return os.path.join(self.tools_dir, tool_filename)

    def get_ffmpeg_path(self):
        tools_path = self.get_tool_path("ffmpeg.exe")
        if os.path.exists(tools_path):
            return tools_path
        
        # Check system PATH
        return "ffmpeg"

    def get_extra_yt_dlp_args(self):
        """Return extra yt-dlp arguments for anti-bot and JS runtimes."""
        args = []
        
        # 1. JS Runtime (Deno)
        deno_p = self.get_tool_path("deno.exe")
        if os.path.exists(deno_p):
            args.extend(["--js-runtimes", f"deno:{deno_p}"])
            
        # 2. Anti-bot Measures (Cloudflare bypass)
        # Use impersonate to mimic a real browser
        args.extend(["--extractor-args", "generic:impersonate"])
        
        # 3. Modern User-Agent
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        args.extend(["--user-agent", ua])
        
        return args

    def open_download_folder(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        os.startfile(os.path.abspath(self.output_dir))

    # --- Core Management ---
    def check_core_status(self):
        self.yt_dlp_path = self.get_tool_path("yt-dlp.exe")
        self.deno_path = self.get_tool_path("deno.exe")

        missing = []
        if not os.path.exists(self.yt_dlp_path):
            missing.append("yt-dlp")
        if not os.path.exists(self.deno_path):
            missing.append("Deno")
        if not os.path.exists(self.get_tool_path("ffmpeg.exe")) and self.get_ffmpeg_path() == "ffmpeg":
            missing.append("FFmpeg")
            
        if missing:
            self.log(f"⚠️ 偵測到缺少組件 ({', '.join(missing)})，將自動下載補齊...")
            self.start_update_thread()
        else:
            self.log("✅ 核心組件檢查 (yt-dlp, FFmpeg, Deno): OK")
            self.after(0, lambda: self.download_btn.configure(state="normal"))

    def start_update_thread(self):
        self.update_btn.configure(state="disabled", text="更新中...")
        self.download_btn.configure(state="disabled") # Disable download button during updates
        threading.Thread(target=self.run_update_task, daemon=True).start()

    def run_update_task(self):
        self.log("正在檢查並更新核心組件...")
        
        # Helper nested function for streaming downloads with progress reporting
        def download_with_progress(url, description):
            buf = io.BytesIO()
            try:
                resp = requests.get(url, stream=True, timeout=(15, 30))
                resp.raise_for_status()
                total_size = int(resp.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in resp.iter_content(chunk_size=131072): # 128KB chunks
                    if chunk:
                        buf.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = downloaded / total_size
                            self.after(0, self._update_progress_simple, percent, description)
                return buf
            except Exception as e:
                self.log(f"⚠️ {description} 下載失敗: {e}")
                self.log("💡 提示：若網路連線阻擋，請手動將 tools 資料夾 (含 yt-dlp.exe, ffmpeg.exe, deno.exe) 複製到程式目錄中。")
                return None

        # 1. Download/Update yt-dlp
        target_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        if not os.path.exists(self.yt_dlp_path):
            self.log(f"正在下載核心: {target_url}")
            buf = download_with_progress(target_url, "核心 (yt-dlp)")
            if buf:
                try:
                    with open(self.yt_dlp_path, 'wb') as f:
                        f.write(buf.getvalue())
                    self.log("核心下載完成！")
                except Exception as e:
                    self.log(f"核心寫入失敗: {e}")
        else:
            try:
                ver_proc = subprocess.run([self.yt_dlp_path, "--version"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                current_ver = ver_proc.stdout.strip()
                self.log(f"目前核心版本: {current_ver}")
            except: pass
            
            self.log("正在執行自我更新指令 (-U)...")
            try:
                subprocess.run([self.yt_dlp_path, "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                try:
                    ver_proc2 = subprocess.run([self.yt_dlp_path, "--version"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    self.log(f"更新後核心版本: {ver_proc2.stdout.strip()}")
                except: pass
                self.log("核心更新程序結束")
            except Exception as e:
                self.log(f"更新執行失敗: {e}")

        # 2. Check/Download Deno (JS runtime for YouTube EJS challenge)
        if not os.path.exists(self.deno_path):
            self.log("正在下載 Deno JS 執行環境 (解決 YouTube EJS 挑戰)...")
            deno_zip_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
            buf = download_with_progress(deno_zip_url, "Deno")
            if buf:
                try:
                    with zipfile.ZipFile(buf) as z:
                        with z.open("deno.exe") as src, open(self.deno_path, "wb") as dst:
                            dst.write(src.read())
                    self.log("✅ Deno 安裝成功！")
                except Exception as e:
                    self.log(f"⚠️ Deno 安裝失敗: {e}")
        else:
            self.log("✅ Deno JS 執行環境: OK")

        # 3. Check/Download FFmpeg
        ffmpeg_target = os.path.join(self.tools_dir, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_target) and self.get_ffmpeg_path() == "ffmpeg":
            self.log("正在下載 FFmpeg...")
            ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            buf = download_with_progress(ffmpeg_url, "FFmpeg")
            if buf:
                try:
                    with zipfile.ZipFile(buf) as z:
                        for name in z.namelist():
                            if name.endswith("bin/ffmpeg.exe"):
                                with z.open(name) as src, open(ffmpeg_target, "wb") as dst:
                                    dst.write(src.read())
                                break
                    self.log("✅ FFmpeg 安裝成功！")
                except Exception as e:
                    self.log(f"⚠️ FFmpeg 安裝失敗: {e}")
                    
        self.after(0, lambda: self.update_btn.configure(state="normal", text="更新核心"))
        self.after(0, lambda: self.download_btn.configure(state="normal")) # Re-enable download button
        self.after(0, lambda: self.status_label.configure(text="準備就緒", text_color=("gray10", "gray90"), font=("Microsoft JhengHei UI", 15, "bold")))
        self.after(0, lambda: self.progress_bar.set(0))
        self.after(0, lambda: self.percent_label.configure(text="0%"))

    def _update_progress_simple(self, percent, description):
        """Update progress bar safely from background thread for core updates."""
        self.progress_bar.set(percent)
        self.percent_label.configure(text=f"{int(percent * 100)}%")
        self.status_label.configure(text=f"正在下載 {description}... ({int(percent * 100)}%)")


    # --- Threads Download Logic ---
    def download_threads_video(self, url):
        """Open threadsdownloader.com and copy URL to clipboard for seamless user experience."""
        import webbrowser
        
        # Clean URL: strip /media if present at the end
        if url.endswith("/media"):
            url = url[:-6]
            
        # threadsdownloader prefers threads.net over threads.com
        url = url.replace("threads.com", "threads.net")
        
        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update() # force clipboard update
        
        # Open site (URL pre-fill is unreliable, so let user paste)
        target = "https://threadsdownloader.com/"
        self.log("   ℹ️ 因 Meta 官方 API 嚴格限制與登入驗證，程式無法直接抓取 Threads 影片")
        self.log("   📋 (已自動將影片網址【複製到剪貼簿】)")
        self.log("   🌐 正在開啟外部下載網站：threadsdownloader.com")
        self.log("   💡 提示：請在網站 Thread Link 輸入框按【Ctrl + V】貼上，再點 Load Videos 按鈕即可。")
        
        webbrowser.open(target)
        return False, "已開啟瀏覽器，請在網站中貼上網址並下載"

    # --- Download Logic ---
    def start_download_thread(self):
        urls_text = self.url_entry.get("1.0", "end-1c").strip()
        if not urls_text or "在此貼上影片網址" in urls_text:
            messagebox.showwarning("提示", "請輸入至少一個影片網址！")
            return
            
        urls = [u.strip() for u in urls_text.split('\n') if u.strip()]
        if not urls:
            messagebox.showwarning("提示", "請輸入有效的影片網址！")
            return
            
        # Range/Clip Validation
        if self.clip_video_var.get():
            start_val = self.start_time_entry.get().strip()
            end_val = self.end_time_entry.get().strip()
            if not start_val and not end_val:
                messagebox.showwarning("提示", "請輸入開始或結束時間！")
                return
            time_pattern = re.compile(r'^(?:\d{1,2}:)?(?:\d{1,2}:)?\d{2}$|^\d+$|^$')
            if not time_pattern.match(start_val) or not time_pattern.match(end_val):
                messagebox.showwarning("提示", "時間格式不正確！\n請輸入 hh:mm:ss、mm:ss 或純秒數 (例如 00:01:30 或 90)。")
                return

        self.url_entry.delete("1.0", 'end') # Clear Entry
            
        if not os.path.exists(self.yt_dlp_path):
             messagebox.showerror("錯誤", "找不到核心檔案，請先點擊「更新核心」下載必要組件。")
             return
        
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.is_downloading = True
        self.progress_bar.set(0)
        
        # --- [NEW] Intercept Playlist URLs ---
        has_playlist = any("list=" in u for u in urls)
        if has_playlist:
            # If there's a mix of playlist and non-playlist, we'll process the first playlist found for now
            playlist_url = next(u for u in urls if "list=" in u)
            self.log(f"偵測到播放清單網址，開始進入解析模式...")
            self.status_label.configure(text="解析播放清單中...", font=("Microsoft JhengHei UI", 15, "bold"))
            threading.Thread(target=self.run_playlist_fetch_task, args=(playlist_url,), daemon=True).start()
        else:
            threading.Thread(target=self.run_download_task, args=(urls,), daemon=True).start()
        # -------------------------------------

    def stop_download(self):
        if self.is_downloading:
            self.is_downloading = False
            self.log("正在停止任務...")
            if self.current_process:
                try:
                    self.current_process.terminate()
                except: pass
            self.stop_btn.configure(state="disabled")
            self.download_btn.configure(state="normal")

    # --- [NEW] Playlist Support ---
    def run_playlist_fetch_task(self, playlist_url):
        import json
        self.log(f"正在擷取清單資訊: {playlist_url}")
        
        # We only want flat metadata, no actual downloading yet
        cmd = [
            self.yt_dlp_path,
            "--flat-playlist",
            "-J", # Dump JSON
            playlist_url
        ] + self.get_extra_yt_dlp_args()
        
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if proc.returncode != 0:
                self.log(f"播放清單解析失敗: {proc.stderr}")
                self.after(0, self.stop_download)
                return
                
            entries = []
            for line in proc.stdout.split('\n'):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if isinstance(data, dict) and "entries" in data and isinstance(data["entries"], list):
                        # Full playlist dictionary
                        for entry in data["entries"]:
                            if isinstance(entry, dict) and (entry.get("title") or entry.get("url") or entry.get("id")):
                                entries.append(entry)
                    elif isinstance(data, dict) and (data.get("title") or data.get("url") or data.get("id")):
                        # Single line JSON for flat playlist
                        entries.append(data)
                except: pass
                
            if not entries:
                self.log("無法解析到任何影片，或此清單不公開。")
                self.after(0, self.stop_download)
                return
                
            self.log(f"成功解析 {len(entries)} 部影片，等待使用者確認...")
            self.after(0, lambda: PlaylistDialog(self, entries))
            
        except Exception as e:
            self.log(f"清單獲取出現錯誤: {e}")
            self.after(0, self.stop_download)

    # show_playlist_dialog removed and replaced by PlaylistDialog class
    # -----------------------------------

    def run_download_task(self, urls):
        import json
        
        selected_fmt = self.format_var.get()
        selected_quality = self.quality_var.get()
        total_urls = len(urls)
        success_count = 0
        
        for idx, url in enumerate(urls, 1):
            if not self.is_downloading:
                self.log("下載已全部停止。")
                break
                
            # 0. Sanitize URL (Remove playlist params to force single video)
            if "youtube.com" in url or "youtu.be" in url:
                if "&list=" in url:
                    url = url.split("&list=")[0]
                if "?list=" in url:
                    url = url.split("?list=")[0]

            # 0.5. Threads platform — use native downloader
            if "threads.com" in url or "threads.net" in url:
                self.log(f"\n[{idx}/{total_urls}] 任務開始 (Threads): {url}")
                self.after(0, lambda: self.progress_bar.set(0))
                self.download_threads_video(url)
                continue
            
            self.log(f"\n[{idx}/{total_urls}] 任務開始 ({selected_fmt}): {url}")
            self.after(0, lambda i=idx, t=total_urls: self.status_label.configure(text=f"任務處理中... ({i}/{t})", font=("Microsoft JhengHei UI", 15, "bold")))
            self.after(0, lambda: self.progress_bar.set(0))
            self.after(0, lambda: self.percent_label.configure(text="0%"))
        
        # 1. Fetch Metadata (Title & Chapters)
            self.log("正在獲取影片資訊...")
            chapters = []
            video_duration = 0
            video_title = "Video"
            
            try:
                # -J = --dump-single-json
                meta_cmd = [self.yt_dlp_path, "-J", "--no-playlist", url] + self.get_extra_yt_dlp_args()
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                meta_proc = subprocess.run(
                    meta_cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if meta_proc.returncode != 0:
                    self.log(f"無法獲取資訊: {meta_proc.stderr}")
                    continue

                video_info = json.loads(meta_proc.stdout)
                video_title = video_info.get("title", "Video")
                video_duration = video_info.get("duration", 0)
                # Sanitize title
                video_title = "".join([c for c in video_title if c.isalnum() or c in " ._-()[]"]).strip()
                self.log(f"目標影片: {video_title}")
                
                # --- [NEW] Download Thumbnail ---
                thumb_url = video_info.get("thumbnail")
                if thumb_url:
                    threading.Thread(target=self.download_thumbnail_bg, args=(thumb_url,), daemon=True).start()
                # --------------------------------
                
                # --- [NEW] Smart Subtitle Picker ---
                target_sub_lang = None
                if self.dl_subs_var.get():
                    pref = self.subs_lang_var.get()
                    lang_prefs = []
                    if "繁體" in pref: lang_prefs = ["zh-Hant", "zh-TW", "zh", "zh-Hans"]
                    elif "簡體" in pref: lang_prefs = ["zh-Hans", "zh-CN", "zh", "zh-Hant"]
                    elif "英文" in pref: lang_prefs = ["en", "en-US", "en-GB"]
                    elif "日文" in pref: lang_prefs = ["ja", "ja-JP"]
                    else: lang_prefs = ["zh-Hant", "zh-TW", "zh", "zh-Hans", "en", "ja"]
                    
                    available_subs = list(video_info.get("subtitles", {}).keys())
                    available_auto = list(video_info.get("automatic_captions", {}).keys())
                    
                    for p in lang_prefs:
                        if p in available_subs:
                            target_sub_lang = p
                            self.log(f"成功找到官方字幕軌道: {p}")
                            break
                            
                    if not target_sub_lang:
                        for p in lang_prefs:
                            if p in available_auto:
                                target_sub_lang = p
                                self.log(f"未提供官方字幕，改採 AI 自動生成字幕: {p}")
                                break
                    
                    if not target_sub_lang:
                        self.log("找不到符合偏好的字幕語言，將略過字幕下載以避免連線阻擋異常。")
                # -----------------------------------
                
                chapters = video_info.get("chapters") 
                
                # --- Fallback: Parse Description if chapters are missing ---
                if not chapters and self.split_chapters_var.get():
                    self.log("系統未偵測到內建章節，嘗試從說明欄分析時間軸...")
                    description = video_info.get("description", "")
                    chapters = self.parse_chapters_from_description(description, video_duration)
                    if chapters:
                        self.log(f"分析出 {len(chapters)} 個章節")
                # -----------------------------------------------------------
                
                if self.split_chapters_var.get() and not chapters:
                    self.log("注意: 此影片沒有章節資訊，將只下載完整影片。")
                
                if self.split_chapters_var.get() and chapters:
                    self.log(f"確認將分割為 {len(chapters)} 個章節")
                
            except Exception as e:
                self.log(f"元數據解析失敗: {e}")
                continue

            # 2. Download Full Video
            needs_wmv_convert = False
            fmt_for_ext = selected_fmt
            if selected_fmt == "WMV":
                selected_fmt = "MP4"
                needs_wmv_convert = True

            # Check for name collision and resolve by appending _01, _02, etc.
            unique_title = video_title
            counter = 1
            while True:
                collision = False
                if self.split_chapters_var.get():
                    check_dir = os.path.join(self.output_dir, unique_title)
                    if os.path.exists(check_dir):
                        collision = True
                else:
                    ext_lower = "wmv" if fmt_for_ext == "WMV" else fmt_for_ext.lower()
                    check_file = os.path.join(self.output_dir, f"{unique_title}.{ext_lower}")
                    if os.path.exists(check_file):
                        collision = True
                    if fmt_for_ext == "WMV":
                        for ext in ["mp4", "mkv", "webm", "wmv"]:
                            if os.path.exists(os.path.join(self.output_dir, f"{unique_title}_temp_wmv.{ext}")):
                                collision = True
                                break
                if not collision:
                    break
                unique_title = f"{video_title}_{counter:02d}"
                counter += 1

            video_title = unique_title

            if self.split_chapters_var.get():
                video_dir = os.path.join(self.output_dir, video_title)
                if not os.path.exists(video_dir):
                    os.makedirs(video_dir)
            else:
                video_dir = self.output_dir 

            if needs_wmv_convert:
                out_tmpl = os.path.join(video_dir, f"{video_title}_temp_wmv.%(ext)s")
            else:
                out_tmpl = os.path.join(video_dir, f"{video_title}.%(ext)s")
            found_ffmpeg = self.get_tool_path("ffmpeg.exe")
            ffmpeg_location = os.path.dirname(found_ffmpeg) if os.path.exists(found_ffmpeg) else None
            
            download_success = False
            self.downloaded_file = None
            retry_without_subs = False
            subtitle_429_error = False
            
            for attempt in range(2):
                cmd = [
                    self.yt_dlp_path, url, 
                    "-o", out_tmpl, 
                    "--no-playlist", 
                    "--newline", 
                    "--encoding", "utf-8"
                ] + self.get_extra_yt_dlp_args()
                
                # --- 裁剪模式：計算片段參數並設定 --download-sections ---
                clip_duration = None
                clip_start_secs = None
                clip_end_secs = None
                clip_mode = self.clip_video_var.get()
                
                if clip_mode:
                    start_val = self.start_time_entry.get().strip()
                    end_val = self.end_time_entry.get().strip()
                    if start_val or end_val:
                        def parse_to_seconds(t_str):
                            if not t_str: return None
                            try:
                                if ':' in t_str:
                                    parts = t_str.split(':')
                                    if len(parts) == 3:
                                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                    elif len(parts) == 2:
                                        return int(parts[0]) * 60 + int(parts[1])
                                return int(t_str)
                            except:
                                return None
                        
                        clip_start_secs = parse_to_seconds(start_val) or 0
                        clip_end_secs = parse_to_seconds(end_val) or video_duration
                        if clip_end_secs and clip_end_secs > clip_start_secs:
                            clip_duration = clip_end_secs - clip_start_secs
                            
                            # 格式化為 hh:mm:ss 格式傳給 yt-dlp
                            def secs_to_time(s):
                                h = int(s // 3600)
                                m = int((s % 3600) // 60)
                                sec = int(s % 60)
                                return f"{h:02d}:{m:02d}:{sec:02d}"
                                
                            start_time_str = secs_to_time(clip_start_secs)
                            end_time_str = secs_to_time(clip_end_secs)
                            
                            cmd.extend(["--download-sections", f"*{start_time_str}-{end_time_str}"])
                            cmd.extend(["--downloader-args", "ffmpeg_i:-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"])
                            self.log(f"📋 設定下載片段範圍: {start_time_str} 至 {end_time_str} (共 {clip_duration} 秒)")
                    else:
                        clip_mode = False
                
                # --- [NEW] Add Subtitle Options ---
                if self.dl_subs_var.get() and target_sub_lang and not retry_without_subs:
                    cmd.extend([
                        "--write-subs",
                        "--write-auto-subs",
                        "--sub-langs", target_sub_lang,
                        "--convert-subs", "srt"
                    ])
                # ----------------------------------
                
                if ffmpeg_location:
                    cmd.extend(["--ffmpeg-location", ffmpeg_location])
                    
                if selected_fmt in ["MP4", "MKV", "MOV"]:
                    h_str = ""
                    if "2160p" in selected_quality: h_str = "[height<=2160]"
                    elif "1440p" in selected_quality: h_str = "[height<=1440]"
                    elif "1080p" in selected_quality: h_str = "[height<=1080]"
                    elif "720p" in selected_quality: h_str = "[height<=720]"
                    elif "480p" in selected_quality: h_str = "[height<=480]"

                    # Prioritize H.264 (avc1) + m4a audio, fallback to any video+audio, fallback to best progressive stream
                    # NEVER fallback to audio-only (bestaudio) when downloading a video format!
                    vid_fmt = (
                        f"bestvideo{h_str}[vcodec^=avc1]+bestaudio[ext=m4a]/"
                        f"bestvideo{h_str}[vcodec^=avc1]+bestaudio/"
                        f"bestvideo{h_str}+bestaudio[ext=m4a]/"
                        f"bestvideo{h_str}+bestaudio/"
                        f"best{h_str}/"
                        f"best"
                    )
                    
                    cmd.extend(["-f", vid_fmt])
                    
                    if selected_fmt in ["MP4", "MOV"]:
                        cmd.extend(["--postprocessor-args", "Merger:-c:a aac"])

                    if selected_fmt in ["MP4", "MOV", "MKV"]:
                        cmd.extend(["--merge-output-format", selected_fmt.lower()])

                    if selected_fmt == "MOV":
                         cmd.extend(["--remux-video", "mov"])
                    else:
                         cmd.extend(["--remux-video", selected_fmt.lower()])
                    
                elif selected_fmt == "MP3":
                    cmd.extend(["-x", "--audio-format", "mp3"])
                elif selected_fmt == "WAV":
                    cmd.extend(["-x", "--audio-format", "wav"])

                self.log(f"開始下載檔案..." if not retry_without_subs else f"重新開始下載影片 (略過字幕)...")

                try:
                    # 設定 PYTHONUNBUFFERED 確保 yt-dlp 進度輸出不被緩衝
                    dl_env = os.environ.copy()
                    dl_env['PYTHONUNBUFFERED'] = '1'
                    
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace",
                        env=dl_env,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )

                    # --- [NEW] Expanded Progress Regex to capture Speed, ETA, Size ---
                    # Example yt-dlp output format: [download]  10.5% of ~1.23GiB at  5.00MiB/s ETA 00:30
                    # or: [download]  10.5% of 1.23GiB at 5.00MiB/s ETA 00:30
                    progress_pattern = re.compile(r'\[download\]\s+(?:(?P<percent>\d+\.?\d+)%|.*?)\s+(?:of\s+~?(?P<size>[a-zA-Z0-9.]+)|.*?)\s+(?:at\s+(?P<speed>[a-zA-Z0-9./]+)|.*?)\s+(?:ETA\s+(?P<eta>[\d:]+)|.*?)')
                    simple_percent_pattern = re.compile(r'\[download\]\s+(\d+\.?\d+)%')
                    ffmpeg_progress_pattern = re.compile(r'size=\s*(?P<size>[^\s]+)\s+time=(?P<time>[\d:.]+)\s+bitrate=.*?speed=\s*(?P<speed>[^\s]+)')
                    subtitle_429_error = False
                    # -----------------------------------------------------------------
                    
                    for line in self.current_process.stdout:
                        line = line.strip()
                        if not line:
                            continue
                        
                        if not self.is_downloading:
                            self.current_process.kill()
                            self.log("已停止下載任務")
                            break
                            
                        if "HTTP Error 429" in line:
                            subtitle_429_error = True
                            
                        # Try detailed match first
                        match = progress_pattern.search(line)
                        if match and match.group('percent'):
                            percent_str = match.group('percent')
                            speed_str = match.group('speed') or "--"
                            eta_str = match.group('eta') or "--:--"
                            size_str = match.group('size') or "--"
                            
                            percent = float(percent_str) / 100.0
                            self.after(0, self.update_progress, percent)
                            self.after(0, lambda s=speed_str, e=eta_str, sz=size_str: self.update_speed_labels(s, e, sz))
                        else:
                            # Try ffmpeg progress match
                            ff_match = ffmpeg_progress_pattern.search(line)
                            if ff_match and clip_duration:
                                time_str = ff_match.group('time')
                                speed_str = ff_match.group('speed')
                                size_str = ff_match.group('size')
                                
                                # Convert time_str (hh:mm:ss.xx) to seconds
                                def time_str_to_seconds(t_str):
                                    try:
                                        parts = t_str.split(':')
                                        if len(parts) == 3:
                                            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                                        elif len(parts) == 2:
                                            return float(parts[0]) * 60 + float(parts[1])
                                        return float(parts[0])
                                    except:
                                        return 0.0
                                
                                curr_secs = time_str_to_seconds(time_str)
                                percent = min(1.0, curr_secs / clip_duration)
                                
                                # Calculate ETA
                                try:
                                    speed_val = float(speed_str.replace('x', '').strip())
                                    if speed_val > 0:
                                        rem_secs = (clip_duration - curr_secs) / speed_val
                                        if rem_secs > 0:
                                            eta_str = str(datetime.timedelta(seconds=int(rem_secs)))
                                            if eta_str.startswith('0:'):
                                                eta_str = eta_str[2:]
                                        else:
                                            eta_str = "00:00"
                                    else:
                                        eta_str = "--:--"
                                except:
                                    eta_str = "--:--"
                                    
                                self.after(0, self.update_progress, percent)
                                self.after(0, lambda s=speed_str, e=eta_str, sz=size_str: self.update_speed_labels(f"處理速度: {s}", e, sz))
                            else:
                                # Fallback for simple percentage
                                simple_match = simple_percent_pattern.search(line)
                                if simple_match:
                                    percent = float(simple_match.group(1)) / 100.0
                                    self.after(0, self.update_progress, percent)
                                else:
                                    if any(k in line for k in ["Destination", "Merging", "Error", "Warning", "Deleting", "ERROR"]):
                                        t_line = line.replace("[download] Destination:", "📁 目標路徑:")
                                        t_line = t_line.replace("[Merger] Merging formats into", "🔀 正在合併影音至:")
                                        t_line = t_line.replace("Deleting original file", "🗑️ 刪除原始暫存檔")
                                        t_line = t_line.replace("(pass -k to keep)", "")
                                        self.log(t_line.strip())
                        
                        # 追蹤下載檔案路徑
                        if "Destination:" in line:
                            try:
                                path_part = line.split("Destination:", 1)[1].strip()
                                self.downloaded_file = path_part
                            except: pass
                        elif "Merging formats into" in line:
                            try:
                                path = line.split('"', 1)[1].rsplit('"', 1)[0]
                                self.downloaded_file = path
                            except: pass
                        elif "has already been downloaded" in line:
                            try:
                                path = line.split('[download]', 1)[1].split('has already been downloaded', 1)[0].strip()
                                self.downloaded_file = path
                            except: pass

                    self.current_process.wait()
                    if self.current_process.returncode == 0 and self.is_downloading and not subtitle_429_error:
                        download_success = True
                        break # Exit the retry loop
                    else:
                        if subtitle_429_error and not retry_without_subs:
                            self.log("⚠️ 偵測到 YouTube 字幕伺服器阻擋 (Error 429)，將自動取消字幕並重新下載影片！")
                            retry_without_subs = True
                            continue # Loop again (attempt 2)
                        else:
                            if not subtitle_429_error:
                                self.log("下載失敗或已被中斷")
                            break # No more retries or it was manually stopped
                        
                except Exception as e:
                    self.log(f"下載執行錯誤: {e}")
                    break
                
            # 3. Post-download Processing
            if download_success and self.is_downloading:
                success_count += 1
                
                # 3a. 章節分割模式
                if self.split_chapters_var.get() and chapters and self.downloaded_file and os.path.exists(self.downloaded_file):
                    self.manual_split_chapters(self.downloaded_file, chapters, video_dir, selected_fmt, ffmpeg_location, needs_wmv_convert)
                elif needs_wmv_convert and self.downloaded_file:
                    self.convert_to_wmv(self.downloaded_file, ffmpeg_location)
                self.log(f"[{idx}/{total_urls}] 當前任務完成！")

        # After all urls
        self.log(f"所有任務處理完畢。成功完成 {success_count}/{total_urls} 個檔案。")
        self.after(0, lambda: messagebox.showinfo("批量下載完成", f"完成 {success_count}/{total_urls} 個檔案下載。"))
        self.after(0, self.finish_download)

    # --- [NEW] Helpers for Thumbnails & Speeds ---
    def update_speed_labels(self, speed, eta, size):
        if speed.startswith("處理速度: "):
            speed = speed.replace("處理速度: ", "") + " (倍速轉檔)"
            
        formatted_size = size
        if size:
            size_clean = size.strip()
            match = re.match(r'^([0-9.]+)\s*([a-zA-Z]+)$', size_clean)
            if match:
                val_str, unit = match.groups()
                try:
                    val = float(val_str)
                    unit_upper = unit.upper()
                    if unit_upper in ["KIB", "KB"]:
                        if val >= 1024:
                            formatted_size = f"{val/1024:.2f} MB"
                        else:
                            formatted_size = f"{val:.1f} KB"
                    elif unit_upper in ["MIB", "MB"]:
                        formatted_size = f"{val:.2f} MB"
                    elif unit_upper in ["GIB", "GB"]:
                        formatted_size = f"{val:.2f} GB"
                except:
                    pass
            formatted_size = formatted_size.replace("KiB", "KB").replace("MiB", "MB").replace("GiB", "GB")

        self.speed_label.configure(text=f"速度: {speed}")
        self.eta_label.configure(text=f"預計: {eta}")
        self.size_label.configure(text=f"大小: {formatted_size}")

    def download_thumbnail_bg(self, url):
        from PIL import Image, ImageTk
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                img_data = resp.content
                img = Image.open(io.BytesIO(img_data))
                
                # Resize keeping aspect ratio, crop to 16:9 240x135
                # Basic crop/resize
                w, h = img.size
                target_ratio = 16/9
                current_ratio = w/h
                if current_ratio > target_ratio:
                    # Too wide, crop width
                    new_w = int(h * target_ratio)
                    offset = (w - new_w) // 2
                    img = img.crop((offset, 0, offset + new_w, h))
                else:
                    # Too tall, crop height
                    new_h = int(w / target_ratio)
                    offset = (h - new_h) // 2
                    img = img.crop((0, offset, w, offset + new_h))
                    
                img = img.resize((240, 135), Image.Resampling.LANCZOS)
                
                self.current_thumb_tk = ImageTk.PhotoImage(img) # Keep reference
                self.after(0, lambda: self.thumbnail_canvas.create_image(0, 0, image=self.current_thumb_tk, anchor="nw"))
        except Exception as e:
            pass # Ignore thumbnail errors silently
    # ---------------------------------------------

    def parse_chapters_from_description(self, description, duration):
        """
        Regex to find timestamps in description.
        Formats: 00:00, 0:00, 01:23:45
        """
        import re
        lines = description.split('\n')
        # Regex for HH:MM:SS or MM:SS at START of line (supports brackets like [00:00] or (00:00))
        pattern = re.compile(r'^\s*[\(\[\s]*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[\)\]\s]*[\-–—:]?\s*(.*)')
        
        found_chapters = []
        for line in lines:
            match = pattern.match(line)
            if match:
                h, m, s, title = match.groups()
                h = int(h) if h else 0
                m = int(m)
                s = int(s)
                seconds = h * 3600 + m * 60 + s
                
                # Cleanup title
                title = title.strip(" -")
                if not title: title = f"Chapter {len(found_chapters)+1}"
                
                found_chapters.append({
                    "start_time": seconds,
                    "title": title
                })
        
        # Sort by start time just in case
        found_chapters.sort(key=lambda x: x["start_time"])
        
        # Calculate end times
        final_chapters = []
        for i in range(len(found_chapters)):
            start = found_chapters[i]["start_time"]
            title = found_chapters[i]["title"]
            
            if i < len(found_chapters) - 1:
                end = found_chapters[i+1]["start_time"]
            else:
                end = duration # Last chapter ends at video duration
                
            if end > start: # Valid chapter
                final_chapters.append({
                    "start_time": start,
                    "end_time": end,
                    "title": title
                })
                
        return final_chapters

    def manual_split_chapters(self, src_file, chapters, output_dir, fmt, ffmpeg_loc, needs_wmv):
        """
        Manually split video using FFmpeg with re-encoding for precision.
        Format: ffmpeg -ss {start} -i {input} -t {duration} -c:v libx264 -preset ultrafast -c:a aac {output}
        """
        self.log("--- 開始執行精準章節分割 (Precision Split) ---")
        self.progress_bar.set(0)
        
        ffmpeg_exe = "ffmpeg"
        if ffmpeg_loc:
             ffmpeg_exe = os.path.join(ffmpeg_loc, "ffmpeg.exe")
             
        total_chapters = len(chapters)
        
        for i, chapter in enumerate(chapters):
            if not self.is_downloading:
                self.log("分割任務被使用者停止")
                break
                
            title = chapter.get("title", f"Chapter {i+1}")
            # Sanitize filename
            safe_title = "".join([c for c in title if c.isalnum() or c in " ._-"]).strip()
            start_time = chapter.get("start_time")
            end_time = chapter.get("end_time")
            duration = end_time - start_time
            
            # Pad chapter number
            ext = 'wmv' if needs_wmv else fmt.lower()
            filename = f"{i+1:03d} - {safe_title}.{ext}"
            out_path = os.path.join(output_dir, filename)
            
            self.log(f"[{i+1}/{total_chapters}] 正在處理: {title} ({duration:.1f}s)")
            self.status_label.configure(text=f"正在分割: 第 {i+1} / {total_chapters} 章")
            self.update_progress((i) / total_chapters)
            
            # Construct FFmpeg Command
            # -ss before -i is fast seek (keyframes). 
            # With re-encoding, it should be accurate.
            
            cmd = [
                ffmpeg_exe, "-y",
                "-ss", str(start_time),
                "-i", src_file,
                "-t", str(duration),
            ]
            
            # Encoder Settings
            if fmt in ["MP4", "MOV", "MKV", "WMV"]:
                if fmt == "WMV" or needs_wmv:
                    # WMV settings
                    cmd.extend(["-c:v", "wmv2", "-q:v", "4", "-c:a", "wmav2"])
                else: # MP4/MOV/MKV
                    # Use libx264 ultrafast for speed + precision
                    cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-c:a", "aac"])
            elif fmt in ["MP3", "WAV"]:
                # Audio only split
                if fmt == "MP3": cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
                elif fmt == "WAV": cmd.extend(["-c:a", "pcm_s16le"])
            
            cmd.append(out_path)
            
            try:
                # Log cmd for debug (optional, maybe too verbose)
                # print(" ".join(cmd))
                
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                self.log(f"❌ 章節 {i+1} 分割失敗: {e}")
            
        self.update_progress(1.0)
        self.log("所有章節分割完畢！")
        
        # Cleanup: Ask user or auto-delete full file? 
        # Usually user expects only chapters? Let's keep full file for safety or delete?
        # User goal is "Split", implies they want parts.
        # But keeping full file is safer. Let's leave it.
    
    def convert_to_wmv(self, src, ffmpeg_loc):
        # ... (Existing logic moved here if needed or just kept inline)
        pass # Simplified for now as it's handled in the loop logic for chapters, 
             # but for single file non-split WMV:
             
        self.log("正在轉換為 WMV...")
        ffmpeg_exe = "ffmpeg"
        if ffmpeg_loc: ffmpeg_exe = os.path.join(ffmpeg_loc, "ffmpeg.exe")
        
        wmv_path = os.path.splitext(src)[0] + ".wmv"
        cmd = [
            ffmpeg_exe, "-y", "-i", src,
            "-c:v", "wmv2", "-q:v", "4", "-c:a", "wmav2",
            wmv_path
        ]
        try:
             subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, check=True)
             self.log("WMV 轉換成功")
             try: os.remove(src) 
             except: pass
        except Exception as e:
             self.log(f"WMV 轉換失敗: {e}")

    def update_progress(self, percent):
        self.progress_bar.set(percent)
        self.percent_label.configure(text=f"{int(percent*100)}%")

    def finish_download(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="準備就緒")
        self.current_process = None
