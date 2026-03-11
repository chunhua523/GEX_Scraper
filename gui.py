import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading
import asyncio
import os
from datetime import datetime
from scraper import LietaScraper
import utils
from tkcalendar import Calendar
# from scraper import LietaScraper

class LietaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Lieta Research Scraper")
        self.geometry(f"{900}x{600}")

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create layouts
        self.create_sidebar()
        self.create_main_area()
        
        self.load_settings()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        
        self.current_log_file = None
        self.last_run_date = None
        self.last_failed_tasks = []  # Store failed tasks for retry
        self.check_schedule()

    def check_schedule(self):
        """Checks every 10s if we need to run the scheduled task."""
        if self.var_schedule_en.get():
            now = datetime.now()
            # day_name = now.strftime("%A") 
            day_index = now.weekday() # 0 = Monday, ..., 4 = Friday
            current_time = now.strftime("%H:%M")
            
            target_time = self.entry_time.get()
            
            # Check: Mon-Fri (0-4), Time matches (within this minute), and haven't run today
            if 0 <= day_index <= 4 and current_time == target_time:
                today_str = now.strftime("%Y-%m-%d")
                if self.last_run_date != today_str:
                    if self.btn_start.cget("state") != "disabled":
                        self.log(f"Auto-Schedule Triggered (Mon-Fri) at {target_time}")
                        self.last_run_date = today_str
                        self.on_start(skip_selection_dialog=True)
                    else:
                        self.log("Skipping Schedule: Job already running.")
        
        self.after(10000, self.check_schedule)
    
    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Lieta Scraper", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

    def create_main_area(self):
        # Main scrollable container
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # 1. Top Bar: Login + Browser Selection
        self.top_bar = ctk.CTkFrame(self.main_frame)
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 15))
        
        self.btn_login = ctk.CTkButton(self.top_bar, text="Log in via Browser", command=self.on_login_click, width=140)
        self.btn_login.pack(side="left", padx=15, pady=10)
        
        self.lbl_login_status = ctk.CTkLabel(self.top_bar, text="Not Logged In", text_color="red", font=("", 12, "bold"))
        self.lbl_login_status.pack(side="left", padx=5)

        # Browser Selection (Right aligned in top bar)
        self.var_browser = ctk.StringVar(value="chrome")
        radio_brave = ctk.CTkRadioButton(self.top_bar, text="Brave", variable=self.var_browser, value="brave", width=60)
        radio_brave.pack(side="right", padx=15)
        radio_chrome = ctk.CTkRadioButton(self.top_bar, text="Chrome", variable=self.var_browser, value="chrome", width=70)
        radio_chrome.pack(side="right", padx=5)
        ctk.CTkLabel(self.top_bar, text="Browser:").pack(side="right", padx=5)


        # 2. Main Config Area - Two Columns
        # Left: Standard Platform
        self.std_frame = ctk.CTkFrame(self.main_frame)
        self.std_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.std_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.std_frame, text="Standard Platform", font=("", 16, "bold")).pack(pady=(10, 5), anchor="w", padx=15)
        
        # Standard Ticker Row
        self.std_ticker_row = ctk.CTkFrame(self.std_frame, fg_color="transparent")
        self.std_ticker_row.pack(padx=15, pady=5, fill="x", anchor="w")
        
        # Row 1: Select button and Manage button
        btn_row = ctk.CTkFrame(self.std_ticker_row, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 2))
        
        self.btn_ticker_file = ctk.CTkButton(btn_row, text="Select Ticker List", command=self.select_ticker_file, width=140)
        self.btn_ticker_file.pack(side="left")
        
        self.btn_manage_tickers = ctk.CTkButton(btn_row, text="✏️ Manage", command=self.open_ticker_manager_std, width=100, fg_color="transparent", border_width=1, border_color="gray")
        self.btn_manage_tickers.pack(side="left", padx=(5, 0))
        
        # Row 2: File name label
        self.lbl_ticker_file = ctk.CTkLabel(self.std_ticker_row, text="No file selected", font=("", 11), text_color="#DCE4EE", anchor="w")
        self.lbl_ticker_file.pack(fill="x", pady=(0, 0))

        # Standard Models Grid
        ctk.CTkLabel(self.std_frame, text="Models:", font=("", 13, "bold")).pack(padx=15, pady=(5,0), anchor="w")
        self.range_std_models = ctk.CTkFrame(self.std_frame, fg_color="transparent")
        self.range_std_models.pack(padx=10, pady=5, fill="x")
        
        self.model_vars = {}
        standard_models = ["Gamma", "Delta", "Theta", "Term", "Smile", "Levels", "Table", "TV Code"] 
        for i, model in enumerate(standard_models):
            var = ctk.StringVar(value="off")
            chk = ctk.CTkCheckBox(self.range_std_models, text=model, variable=var, onvalue=model, offvalue="off", font=("", 12))
            chk.grid(row=i//2, column=i%2, sticky="w", padx=5, pady=5) # 2 columns
            self.model_vars[model] = var


        # Right: CME Platform
        self.cme_frame = ctk.CTkFrame(self.main_frame)
        self.cme_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.cme_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.cme_frame, text="CME Platform", font=("", 16, "bold")).pack(pady=(10, 5), anchor="w", padx=15)

        # CME Ticker Row
        self.cme_ticker_row = ctk.CTkFrame(self.cme_frame, fg_color="transparent")
        self.cme_ticker_row.pack(padx=15, pady=5, fill="x", anchor="w")

        # Row 1: Select button and Manage button
        cme_btn_row = ctk.CTkFrame(self.cme_ticker_row, fg_color="transparent")
        cme_btn_row.pack(fill="x", pady=(0, 2))

        self.btn_cme_ticker = ctk.CTkButton(cme_btn_row, text="Select CME Ticker List", command=self.select_cme_ticker_file, width=140)
        self.btn_cme_ticker.pack(side="left")
        
        self.btn_manage_cme_tickers = ctk.CTkButton(cme_btn_row, text="✏️ Manage", command=self.open_ticker_manager_cme, width=100, fg_color="transparent", border_width=1, border_color="gray")
        self.btn_manage_cme_tickers.pack(side="left", padx=(5, 0))
        
        # Row 2: File name label
        self.lbl_cme_ticker = ctk.CTkLabel(self.cme_ticker_row, text="No file selected", font=("", 11), text_color="#DCE4EE", anchor="w")
        self.lbl_cme_ticker.pack(fill="x", pady=(0, 0))

        # CME Models Grid
        ctk.CTkLabel(self.cme_frame, text="Models:", font=("", 13, "bold")).pack(padx=15, pady=(5,0), anchor="w")
        self.range_cme_models = ctk.CTkFrame(self.cme_frame, fg_color="transparent")
        self.range_cme_models.pack(padx=10, pady=5, fill="x")

        self.cme_model_vars = {}
        cme_models = ["Gamma", "Delta", "Smile", "Term", "TV Code"]
        for i, model in enumerate(cme_models):
            var = ctk.StringVar(value="off")
            chk = ctk.CTkCheckBox(self.range_cme_models, text=model, variable=var, onvalue=model, offvalue="off", font=("", 12))
            chk.grid(row=i//2, column=i%2, sticky="w", padx=5, pady=5) # 2 columns
            self.cme_model_vars[model] = var


        # 3. Global Configuration (Download Path + Settings)
        self.global_frame = ctk.CTkFrame(self.main_frame)
        self.global_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=15)
        
        ctk.CTkLabel(self.global_frame, text="Global Configuration", font=("", 14, "bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w", columnspan=2)

        # Row 1: Download Path
        self.btn_dl_path = ctk.CTkButton(self.global_frame, text="Select Download Folder", command=self.select_download_path, width=180)
        self.btn_dl_path.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="w")
        self.lbl_dl_path = ctk.CTkLabel(self.global_frame, text="No folder selected", font=("", 12), text_color="#DCE4EE")
        self.lbl_dl_path.grid(row=1, column=1, padx=5, pady=(5, 10), sticky="w")

        # Row 2: View Files Button (New)
        self.btn_view_files = ctk.CTkButton(self.global_frame, text="📂 View Scraped Files", command=self.open_file_viewer, width=180)
        self.btn_view_files.grid(row=2, column=0, padx=15, pady=5, sticky="w")

        # Row 3: Parallel Switch
        self.var_parallel = ctk.BooleanVar(value=False)
        self.chk_parallel = ctk.CTkSwitch(self.global_frame, text="Multi-window Mode (Scrape Std & CME in parallel)", variable=self.var_parallel)
        self.chk_parallel.grid(row=3, column=0, columnspan=2, padx=15, pady=5, sticky="w")

        # Row 4: Schedule Section
        self.schedule_subframe = ctk.CTkFrame(self.global_frame, fg_color="transparent")
        self.schedule_subframe.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=(5, 15))
        
        ctk.CTkLabel(self.schedule_subframe, text="Auto-Schedule (Mon-Fri):", font=("",12,"bold")).pack(side="left", padx=(0, 10))
        
        self.entry_time = ctk.CTkEntry(self.schedule_subframe, placeholder_text="09:00", width=80)
        self.entry_time.pack(side="left", padx=(0, 15))
        
        self.var_schedule_en = ctk.BooleanVar(value=False)
        self.chk_schedule = ctk.CTkSwitch(self.schedule_subframe, text="Enable Auto-Run", variable=self.var_schedule_en)
        self.chk_schedule.pack(side="left")


        # 4. Action Buttons
        self.action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        
        self.btn_start = ctk.CTkButton(self.action_frame, text="START SCRAPING", fg_color="#2CC985", hover_color="#229C68", height=40, font=("", 14, "bold"), command=self.on_start)
        self.btn_start.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        self.btn_stop = ctk.CTkButton(self.action_frame, text="STOP", fg_color="#FF4D4D", hover_color="#CC0000", state="disabled", height=40, font=("", 14, "bold"), command=self.on_stop)
        self.btn_stop.pack(side="right", padx=(10, 0), expand=True, fill="x")

        self.btn_retry = ctk.CTkButton(self.action_frame, text="RETRY FAILED", fg_color="#FFA500", hover_color="#FF8C00", state="disabled", height=40, font=("", 14, "bold"), command=self.on_retry)
        self.btn_retry.pack(side="right", padx=(10, 0), expand=True, fill="x")

        # 6. Console
        self.console_label = ctk.CTkLabel(self.main_frame, text="Logs:")
        self.console_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=20)
        
        self.console = ctk.CTkTextbox(self.main_frame, height=150)
        self.console.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=20, pady=(0, 20))
        
        # State variables
        self.ticker_filepath = None
        self.cme_ticker_filepath = None
        self.download_folder = None
    
    
    def on_login_click(self):
        self.btn_login.configure(state="disabled")
        browser_type = self.var_browser.get()
        self.log(f"Initializing Login Browser ({browser_type})...")
        threading.Thread(target=self._run_login_thread, args=(browser_type,), daemon=True).start()

    def _run_login_thread(self, browser_type):
        try:
            # Create a new scraper instance for login or reuse?
            # Better to reuse internal browser state mechanism.
            # We'll create a scraper instance just for this action or keep a shared one?
            # Shared one is better if we want to keep browser open, but here we save state to disk.
            # So ad-hoc instance is fine.
            # So ad-hoc instance is fine.
            # So ad-hoc instance is fine.
            scraper = LietaScraper(logger_func=self.log_safe, browser_type=browser_type)
            # Must run all steps in the same event loop
            asyncio.run(scraper.perform_login_flow())
            
            # Update status on main thread
            self.after(0, lambda: self.lbl_login_status.configure(text="Session Saved", text_color="green"))
        except Exception as e:
            self.log_safe(f"Login error: {e}")
        finally:
            self.after(0, lambda: self.btn_login.configure(state="normal"))

    def select_ticker_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text/CSV", "*.txt *.csv")])
        if path:
            self.ticker_filepath = os.path.abspath(path)
            self.lbl_ticker_file.configure(text=os.path.basename(path))
            self.log(f"Selected tickers: {self.ticker_filepath}")

    def select_cme_ticker_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text/CSV", "*.txt *.csv")])
        if path:
            self.cme_ticker_filepath = os.path.abspath(path)
            self.lbl_cme_ticker.configure(text=os.path.basename(path))
            self.log(f"Selected CME tickers: {self.cme_ticker_filepath}")

    def select_download_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_folder = os.path.abspath(path)
            self.lbl_dl_path.configure(text=self.download_folder)
            self.log(f"Selected download folder: {self.download_folder}")

    def on_start(self, skip_selection_dialog=False):
        # Validation
        if not self.download_folder:
            self.log("Error: Please select a download folder.")
            return
        
        selected_models = [m for m, var in self.model_vars.items() if var.get() != "off"]
        selected_cme_models = [m for m, var in self.cme_model_vars.items() if var.get() != "off"]

        tickers = []
        cme_tickers = []

        if selected_models:
            if not self.ticker_filepath:
                self.log("Error: Standard models selected but no Ticker list provided.")
                return
            groups_std = utils.load_tickers_with_groups(self.ticker_filepath)
            tickers = utils.load_tickers_from_file(self.ticker_filepath)
        else:
            groups_std = {}
            tickers = []
        
        if selected_cme_models:
            if not self.cme_ticker_filepath:
                self.log("Error: CME models selected but no CME Ticker list provided.")
                return
            groups_cme = utils.load_tickers_with_groups(self.cme_ticker_filepath)
            cme_tickers = utils.load_tickers_from_file(self.cme_ticker_filepath)
        else:
            groups_cme = {}
            cme_tickers = []
            
        if not selected_models and not selected_cme_models:
            self.log("Error: Please select at least one model (Standard or CME).")
            return

        if not tickers and not cme_tickers:
            return

        if skip_selection_dialog:
            tickers_filtered, cme_tickers_filtered = tickers, cme_tickers
        else:
            result = self._show_ticker_selection_dialog(groups_std, groups_cme)
            if result[0] is None and result[1] is None:
                return
            tickers_filtered, cme_tickers_filtered = result

        parallel = self.var_parallel.get()
        browser_type = self.var_browser.get()

        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.last_failed_tasks = [] # Clear previous failures
        
        # Setup Logger for this run
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = os.path.join("logs", f"run_{timestamp}.log")
        self.log(f"Starting job... (Std: {len(tickers_filtered)} tickers, CME: {len(cme_tickers_filtered)} tickers) Browser: {browser_type}")
        self.log(f"Logging to: {self.current_log_file}")
        
        threading.Thread(target=self._run_job_thread, args=(tickers_filtered, selected_models, cme_tickers_filtered, selected_cme_models, self.download_folder, parallel, browser_type), daemon=True).start()

    def _run_job_thread(self, tickers, models, cme_tickers, cme_models, download_folder, parallel, browser_type):
        self.scraper_instance = LietaScraper(logger_func=self.log_safe, browser_type=browser_type)
        try:
            # Fix: Run everything in one asyncio loop to preserve browser connection
            self.last_failed_tasks = asyncio.run(self.scraper_instance.perform_full_job(tickers, models, cme_tickers, cme_models, download_folder, parallel))
        except Exception as e:
            self.log_safe(f"Job Critical Error: {e}")
        finally:
            self.scraper_instance = None
            self.after(0, self._job_finished)

    def _job_finished(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        
        if self.last_failed_tasks:
            self.btn_retry.configure(state="normal")
            self.log(f"Job finished with {len(self.last_failed_tasks)} failures. You can Retry Failed items.")
        else:
            self.btn_retry.configure(state="disabled")
            self.log("Job finished successfully.")
            
        self.current_log_file = None

    
    def on_stop(self):
        if hasattr(self, 'scraper_instance') and self.scraper_instance:
            self.log("Blocking new requests. Stopping...")
            self.scraper_instance.stop_requested = True
            # Forcing thread stop or asyncio cancel is hard from outside.
            # Best way: Check stop_requested flag in scraper logic.
            
            # If we were using proper asyncio loop integration in GUI we could cancel task.
            # With threading, we rely on the flag check inside scraper logic.

    def on_retry(self):
        if not self.last_failed_tasks:
            self.log("No failed items to retry.")
            return

        selected_tasks = self._show_retry_selection_dialog(self.last_failed_tasks)
        if not selected_tasks:
            return

        self.btn_start.configure(state="disabled")
        self.btn_retry.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        browser_type = self.var_browser.get()
        parallel = self.var_parallel.get()
        
        # Setup Logger for this run
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = os.path.join("logs", f"retry_{timestamp}.log")
        self.log(f"Starting RETRY job... ({len(selected_tasks)} items) Browser: {browser_type}")

        threading.Thread(target=self._run_retry_thread, args=(selected_tasks, self.download_folder, parallel, browser_type), daemon=True).start()

    def _run_retry_thread(self, failed_tasks, download_folder, parallel, browser_type):
        self.scraper_instance = LietaScraper(logger_func=self.log_safe, browser_type=browser_type)
        try:
            # Run retry job
            # returns new failed tasks (if any failed again)
            new_failures = asyncio.run(self.scraper_instance.perform_retry_job(failed_tasks, download_folder, parallel))
            self.last_failed_tasks = new_failures
        except Exception as e:
            self.log_safe(f"Retry Job Critical Error: {e}")
        finally:
            self.scraper_instance = None
            self.after(0, self._job_finished)


    def _show_ticker_selection_dialog(self, groups_std, groups_cme):
        """Show modal dialog to select which tickers to run, grouped by ticker file groups. Returns (tickers_filtered, cme_tickers_filtered) or (None, None) on cancel."""
        self._ticker_dialog_result = (None, None)
        window = ctk.CTkToplevel(self)
        window.title("選擇要執行的 Tickers")
        window.geometry("600x550")
        window.transient(self)
        window.lift()
        window.focus_force()
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)

        top_row = ctk.CTkFrame(window, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_row.grid_columnconfigure(0, weight=1)
        main_scroll = ctk.CTkScrollableFrame(window)
        main_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main_scroll.grid_columnconfigure(0, weight=1)

        std_vars = []
        cme_vars = []

        def add_group_section(platform_label, group_name, ticker_list, var_list):
            if not ticker_list:
                return
            frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
            frame.pack(fill="x", pady=(10, 5))
            frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(frame, text=f"{platform_label} - {group_name} ({len(ticker_list)} tickers)", font=("", 14, "bold")).pack(anchor="w", pady=(0, 5))
            btn_row = ctk.CTkFrame(frame, fg_color="transparent")
            btn_row.pack(fill="x", pady=(0, 3))
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="x")
            group_vars = []
            for t in ticker_list:
                var = ctk.BooleanVar(value=True)
                group_vars.append((t, var))
                var_list.append((t, var))
                ctk.CTkCheckBox(content, text=t, variable=var, font=("", 12)).pack(anchor="w", pady=1)
            def select_all():
                for _, v in group_vars:
                    v.set(True)
            def deselect_all():
                for _, v in group_vars:
                    v.set(False)
            ctk.CTkButton(btn_row, text="全選", command=select_all, width=70, height=28).pack(side="left", padx=(0, 5))
            ctk.CTkButton(btn_row, text="取消全選", command=deselect_all, width=80, height=28, fg_color="transparent", border_width=1).pack(side="left")

        if groups_std:
            for group_name in sorted(groups_std.keys()):
                add_group_section("Standard Platform", group_name, groups_std[group_name], std_vars)
        if groups_cme:
            for group_name in sorted(groups_cme.keys()):
                add_group_section("CME Platform", group_name, groups_cme[group_name], cme_vars)

        def global_select_all():
            for _, v in std_vars:
                v.set(True)
            for _, v in cme_vars:
                v.set(True)
        def global_deselect_all():
            for _, v in std_vars:
                v.set(False)
            for _, v in cme_vars:
                v.set(False)
        ctk.CTkButton(top_row, text="全選", command=global_select_all, width=80, height=28).grid(row=0, column=1, padx=(5, 0))
        ctk.CTkButton(top_row, text="取消全選", command=global_deselect_all, width=90, height=28, fg_color="transparent", border_width=1).grid(row=0, column=2, padx=(5, 0))

        bottom = ctk.CTkFrame(window, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=1)

        def on_confirm():
            tickers_f = [t for t, v in std_vars if v.get()]
            cme_f = [t for t, v in cme_vars if v.get()]
            self._ticker_dialog_result = (tickers_f, cme_f)
            window.destroy()

        def on_cancel():
            self._ticker_dialog_result = (None, None)
            window.destroy()

        ctk.CTkButton(bottom, text="確認並開始", command=on_confirm, width=120, height=35,
                      fg_color="#2CC985", hover_color="#229C68", font=("", 13, "bold")).pack(side="right", padx=5)
        ctk.CTkButton(bottom, text="取消", command=on_cancel, width=120, height=35,
                      fg_color="gray", hover_color="darkgray", font=("", 13, "bold")).pack(side="right")
        window.protocol("WM_DELETE_WINDOW", on_cancel)
        self.wait_window(window)
        return self._ticker_dialog_result

    def _show_retry_selection_dialog(self, failed_tasks):
        """Show modal dialog to select which failed items to retry. Returns list of selected dicts or None on cancel."""
        self._retry_dialog_result = None
        window = ctk.CTkToplevel(self)
        window.title("選擇要重試的失敗項目")
        window.geometry("600x500")
        window.transient(self)
        window.lift()
        window.focus_force()
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(window, text=f"共 {len(failed_tasks)} 個失敗項目，請勾選要重試的項目（預設全選）", font=("", 13)).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        scroll = ctk.CTkScrollableFrame(window)
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        scroll.grid_columnconfigure(0, weight=1)

        item_vars = []
        for item in failed_tasks:
            platform_label = "Standard" if item.get("platform") == "std" else "CME"
            label = f"[{platform_label}] {item.get('model', '')} - {item.get('ticker', '')}"
            var = ctk.BooleanVar(value=True)
            item_vars.append((item, var))
            ctk.CTkCheckBox(scroll, text=label, variable=var, font=("", 12)).pack(anchor="w", pady=2)

        btn_row = ctk.CTkFrame(window, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        btn_row.grid_columnconfigure(0, weight=1)

        def select_all():
            for _, v in item_vars:
                v.set(True)
        def deselect_all():
            for _, v in item_vars:
                v.set(False)
        def on_confirm():
            self._retry_dialog_result = [item for item, v in item_vars if v.get()]
            window.destroy()
        def on_cancel():
            self._retry_dialog_result = None
            window.destroy()

        ctk.CTkButton(btn_row, text="全選", command=select_all, width=70, height=28).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_row, text="取消全選", command=deselect_all, width=80, height=28, fg_color="transparent", border_width=1).pack(side="left")
        ctk.CTkButton(btn_row, text="確認並重試", command=on_confirm, width=120, height=35,
                      fg_color="#2CC985", hover_color="#229C68", font=("", 13, "bold")).pack(side="right", padx=5)
        ctk.CTkButton(btn_row, text="取消", command=on_cancel, width=120, height=35,
                      fg_color="gray", hover_color="darkgray", font=("", 13, "bold")).pack(side="right")
        window.protocol("WM_DELETE_WINDOW", on_cancel)
        self.wait_window(window)
        return self._retry_dialog_result

    def log(self, message):
        timestamp_str = datetime.now().strftime("[%H:%M:%S] ")
        self.console.insert("end", timestamp_str + message + "\n")
        self.console.see("end")
        
        if self.current_log_file:
            try:
                with open(self.current_log_file, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
            except Exception:
                pass
        
    def log_safe(self, message):
        self.after(0, lambda: self.log(message))

    def save_settings(self):
        import json
        settings = {
            "ticker_filepath": os.path.abspath(self.ticker_filepath) if self.ticker_filepath else None,
            "cme_ticker_filepath": os.path.abspath(self.cme_ticker_filepath) if self.cme_ticker_filepath else None,
            "download_folder": os.path.abspath(self.download_folder) if self.download_folder else None,
            "selected_models": [m for m, var in self.model_vars.items() if var.get() != "off"],
            "selected_cme_models": [m for m, var in self.cme_model_vars.items() if var.get() != "off"],
            "parallel": self.var_parallel.get(),
            "browser": self.var_browser.get(),
            "schedule_enabled": self.var_schedule_en.get(),
            "schedule_time": self.entry_time.get()
        }
        try:
            with open("settings.json", "w") as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def load_settings(self):
        import json
        if not os.path.exists("settings.json"):
            return
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
            
            if settings.get("ticker_filepath"):
                self.ticker_filepath = os.path.abspath(settings["ticker_filepath"])
                self.lbl_ticker_file.configure(text=os.path.basename(self.ticker_filepath))
            
            if settings.get("cme_ticker_filepath"):
                self.cme_ticker_filepath = os.path.abspath(settings["cme_ticker_filepath"])
                self.lbl_cme_ticker.configure(text=os.path.basename(self.cme_ticker_filepath))
            
            if settings.get("download_folder"):
                self.download_folder = os.path.abspath(settings["download_folder"])
                self.lbl_dl_path.configure(text=self.download_folder)

            if settings.get("selected_models"):
                for m in settings["selected_models"]:
                    if m in self.model_vars:
                        self.model_vars[m].set(m)
            
            if settings.get("selected_cme_models"):
                for m in settings["selected_cme_models"]:
                    if m in self.cme_model_vars:
                        self.cme_model_vars[m].set(m)
            
            if "parallel" in settings:
                self.var_parallel.set(settings["parallel"])
            
            if "browser" in settings:
                self.var_browser.set(settings["browser"])

            if "schedule_enabled" in settings:
                self.var_schedule_en.set(settings["schedule_enabled"])

            if "schedule_time" in settings:
                self.entry_time.delete(0, "end")
                self.entry_time.insert(0, settings["schedule_time"])
                
        except Exception as e:
            print(f"Failed to load settings: {e}")
            
    def open_file_viewer(self):
        """
        Opens a Toplevel window to list and open files.
        Supports two modes: By Date and By Ticker & Model.
        """
        if not hasattr(self, 'download_folder') or not self.download_folder or not os.path.exists(self.download_folder):
            import tkinter.messagebox
            tkinter.messagebox.showwarning("Warning", "Download folder is not set or invalid.")
            return

        # Create Window
        window = ctk.CTkToplevel(self)
        window.title("View Downloaded Files")
        window.geometry("1100x700")

        window.transient(self)
        window.lift()
        window.focus_force()

        # Grid Layout: row=0 top bar, row=1 main panels
        window.grid_columnconfigure(1, weight=1)
        window.grid_rowconfigure(1, weight=1)

        # =====================================================
        # TOP MODE SWITCHER BAR
        # =====================================================
        top_bar = ctk.CTkFrame(window, height=48, corner_radius=0, fg_color=("#DCDCDC", "#242424"))
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        top_bar.grid_propagate(False)

        ctk.CTkLabel(top_bar, text="View Mode:", font=("", 13), text_color=("gray40", "gray60")).pack(side="left", padx=(20, 8), pady=12)

        seg_mode = ctk.CTkSegmentedButton(top_bar, values=["By Date", "By Ticker & Model"], width=320, height=30)
        seg_mode.set("By Date")
        seg_mode.pack(side="left", pady=10)

        # =====================================================
        # BY DATE: LEFT PANEL
        # =====================================================
        left_panel = ctk.CTkFrame(window, width=280, corner_radius=0)
        left_panel.grid(row=1, column=0, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_panel, text="Control Panel", font=("", 18, "bold"), text_color="#DCE4EE").pack(pady=(20, 10))

        cal_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        cal_container.pack(padx=10, pady=5)

        ctk.CTkLabel(cal_container, text="Select Date:", font=("", 14), anchor="w").pack(fill="x", pady=(0, 5))
        cal = Calendar(cal_container, selectmode='day', date_pattern='yyyy-mm-dd',
                       font=('Arial', 16), cursor="hand2")
        cal.pack()

        cal.bind("<<CalendarSelected>>", lambda e: load_files())

        def go_today():
            today = datetime.now()
            cal.selection_set(today)
            load_files()

        btn_today = ctk.CTkButton(cal_container, text="Today", width=80, height=24,
                                  fg_color="transparent", border_width=1, border_color="gray",
                                  command=go_today)
        btn_today.pack(pady=(5, 0))

        grouped_files = {}
        file_vars = []

        lbl_status = ctk.CTkLabel(left_panel, text="Ready", font=("", 13), text_color="gray")

        # =====================================================
        # BY DATE: RIGHT PANEL
        # =====================================================
        right_panel = ctk.CTkFrame(window, fg_color="transparent")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        seg_models = ctk.CTkSegmentedButton(right_panel)
        seg_models.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        scroll_frame = ctk.CTkScrollableFrame(right_panel)
        scroll_frame.grid(row=1, column=0, sticky="nsew")

        # --- By Date Logic ---

        def update_list(selected_model):
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            file_vars.clear()

            if selected_model == "No Data" or selected_model not in grouped_files:
                ctk.CTkLabel(scroll_frame, text="No files found.", text_color="gray").pack(pady=50)
                return

            tickers = grouped_files[selected_model]

            if "TV Code" in selected_model:
                ticker_groups_std = {}
                ticker_groups_cme = {}
                if hasattr(self, 'ticker_filepath') and self.ticker_filepath and os.path.exists(self.ticker_filepath):
                    ticker_groups_std = utils.load_tickers_with_groups(self.ticker_filepath)
                if hasattr(self, 'cme_ticker_filepath') and self.cme_ticker_filepath and os.path.exists(self.cme_ticker_filepath):
                    ticker_groups_cme = utils.load_tickers_with_groups(self.cme_ticker_filepath)

                ticker_groups = ticker_groups_cme if "CME" in selected_model else ticker_groups_std

                tv_files = []
                for file_key in tickers:
                    fp, dt_obj = tickers[file_key]
                    tv_files.append((dt_obj, fp))
                tv_files.sort(key=lambda x: x[0])

                merged_tv_items = {}
                try:
                    for _, fp in tv_files:
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                ticker_label = "Unknown"
                                if '"' in line:
                                    parts_q = line.split('"')
                                    if len(parts_q) > 1:
                                        ticker_label = parts_q[1]
                                else:
                                    ticker_label = line.split(' ')[0].replace(":", "")
                                merged_tv_items[ticker_label] = line
                        except Exception as e:
                            print(f"Error reading {fp}: {e}")

                    if not merged_tv_items:
                        ctk.CTkLabel(scroll_frame, text="No content found in TV Code files.", text_color="gray").pack(pady=20)
                        return

                    grouped_tv = {}
                    ungrouped_tv = []
                    for ticker in sorted(merged_tv_items.keys()):
                        content = merged_tv_items[ticker]
                        found_group = None
                        for group_name, ticker_list in ticker_groups.items():
                            if ticker in ticker_list:
                                found_group = group_name
                                break
                        if found_group:
                            if found_group not in grouped_tv:
                                grouped_tv[found_group] = []
                            grouped_tv[found_group].append((ticker, content))
                        else:
                            ungrouped_tv.append((ticker, content))

                    for group_name in sorted(grouped_tv.keys()):
                        group_items = grouped_tv[group_name]
                        group_container = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                        group_container.pack(fill="x", padx=10, pady=(10, 5))
                        group_header = ctk.CTkFrame(group_container, fg_color=("#3B3B3B", "#2B2B2B"), corner_radius=5)
                        group_header.pack(fill="x", pady=(0, 2))
                        group_content = ctk.CTkFrame(group_container, fg_color="transparent")
                        group_content.pack(fill="x", pady=(0, 0))
                        is_visible = ctk.BooleanVar(value=True)
                        tv_group_checkboxes = []

                        def create_tv_toggle_function(content, visible_var, button):
                            def toggle():
                                if visible_var.get():
                                    content.pack_forget()
                                    button.configure(text=button.cget("text").replace("▼", "▶"))
                                    visible_var.set(False)
                                else:
                                    content.pack(fill="x", pady=(0, 0))
                                    button.configure(text=button.cget("text").replace("▶", "▼"))
                                    visible_var.set(True)
                            return toggle

                        btn_select_group = ctk.CTkButton(group_header, text="☑", width=30, height=28,
                                                         command=None, fg_color="transparent",
                                                         hover_color=("#4A4A4A", "#3A3A3A"), font=("", 16))
                        btn_select_group.pack(side="left", padx=(5, 0), pady=5)
                        header_middle = ctk.CTkFrame(group_header, fg_color="transparent")
                        header_middle.pack(side="left", fill="x", expand=True)
                        toggle_btn = ctk.CTkButton(header_middle,
                                                   text=f"▼ {group_name} ({len(group_items)} tickers)",
                                                   command=None, fg_color="transparent",
                                                   hover_color=("#4A4A4A", "#3A3A3A"),
                                                   anchor="w", font=("", 13, "bold"))
                        toggle_btn.pack(side="left", fill="x", expand=True, padx=5, pady=5)
                        toggle_btn.configure(command=create_tv_toggle_function(group_content, is_visible, toggle_btn))

                        def create_tv_group_select_all(checkboxes):
                            def select_all_group():
                                all_selected = all(var.get() for var, _ in checkboxes)
                                new_state = not all_selected
                                for var, _ in checkboxes:
                                    var.set(new_state)
                            return select_all_group

                        for t_label, content in group_items:
                            var = ctk.BooleanVar(value=False)
                            chk = ctk.CTkCheckBox(group_content, text=f"{t_label}", variable=var,
                                                  font=("Consolas", 13, "bold"), width=100)
                            chk.pack(anchor="w", padx=20, pady=1)
                            file_vars.append((var, ("TV_DATA", t_label, content)))
                            tv_group_checkboxes.append((var, ("TV_DATA", t_label, content)))
                        btn_select_group.configure(command=create_tv_group_select_all(tv_group_checkboxes))

                    if ungrouped_tv:
                        if grouped_tv:
                            other_header = ctk.CTkFrame(scroll_frame, fg_color=("#3B3B3B", "#2B2B2B"), corner_radius=5)
                            other_header.pack(fill="x", padx=10, pady=(10, 2))
                            ctk.CTkLabel(other_header, text=f"其他 / Other ({len(ungrouped_tv)} tickers)",
                                         font=("", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=5)
                        for t_label, content in ungrouped_tv:
                            var = ctk.BooleanVar(value=False)
                            item_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                            item_frame.pack(fill="x", pady=2, padx=10)
                            chk = ctk.CTkCheckBox(item_frame, text=f"{t_label}", variable=var,
                                                  font=("Consolas", 14, "bold"), width=100)
                            chk.pack(anchor="w", padx=10)
                            file_vars.append((var, ("TV_DATA", t_label, content)))

                except Exception as e:
                    ctk.CTkLabel(scroll_frame, text=f"Error processing TV Code files: {e}", text_color="red").pack(pady=10)
                return

            ticker_groups_std = {}
            ticker_groups_cme = {}
            if hasattr(self, 'ticker_filepath') and self.ticker_filepath and os.path.exists(self.ticker_filepath):
                ticker_groups_std = utils.load_tickers_with_groups(self.ticker_filepath)
            if hasattr(self, 'cme_ticker_filepath') and self.cme_ticker_filepath and os.path.exists(self.cme_ticker_filepath):
                ticker_groups_cme = utils.load_tickers_with_groups(self.cme_ticker_filepath)
            ticker_groups = ticker_groups_cme if "CME" in selected_model else ticker_groups_std

            grouped_tickers = {}
            ungrouped_tickers = []
            for ticker in tickers.keys():
                fp, dt_obj = tickers[ticker]
                found_group = None
                for group_name, ticker_list in ticker_groups.items():
                    if ticker in ticker_list:
                        found_group = group_name
                        break
                if found_group:
                    if found_group not in grouped_tickers:
                        grouped_tickers[found_group] = []
                    grouped_tickers[found_group].append((ticker, fp, dt_obj))
                else:
                    ungrouped_tickers.append((ticker, fp, dt_obj))

            for group_name in sorted(grouped_tickers.keys()):
                group_items = grouped_tickers[group_name]
                group_container = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                group_container.pack(fill="x", padx=10, pady=(10, 5))
                group_header = ctk.CTkFrame(group_container, fg_color=("#3B3B3B", "#2B2B2B"), corner_radius=5)
                group_header.pack(fill="x", pady=(0, 2))
                group_content = ctk.CTkFrame(group_container, fg_color="transparent")
                group_content.pack(fill="x", pady=(0, 0))
                is_visible = ctk.BooleanVar(value=True)
                group_checkboxes = []

                def create_toggle_function(content, visible_var, button):
                    def toggle():
                        if visible_var.get():
                            content.pack_forget()
                            button.configure(text=button.cget("text").replace("▼", "▶"))
                            visible_var.set(False)
                        else:
                            content.pack(fill="x", pady=(0, 0))
                            button.configure(text=button.cget("text").replace("▶", "▼"))
                            visible_var.set(True)
                    return toggle

                btn_select_group = ctk.CTkButton(group_header, text="☑", width=30, height=28,
                                                 command=None, fg_color="transparent",
                                                 hover_color=("#4A4A4A", "#3A3A3A"), font=("", 16))
                btn_select_group.pack(side="left", padx=(5, 0), pady=5)
                header_middle = ctk.CTkFrame(group_header, fg_color="transparent")
                header_middle.pack(side="left", fill="x", expand=True)
                toggle_btn = ctk.CTkButton(header_middle,
                                           text=f"▼ {group_name} ({len(group_items)} tickers)",
                                           command=None, fg_color="transparent",
                                           hover_color=("#4A4A4A", "#3A3A3A"),
                                           anchor="w", font=("", 13, "bold"))
                toggle_btn.pack(side="left", fill="x", expand=True, padx=5, pady=5)
                toggle_btn.configure(command=create_toggle_function(group_content, is_visible, toggle_btn))

                def create_group_select_all(checkboxes):
                    def select_all_group():
                        all_selected = all(var.get() for var, _ in checkboxes)
                        new_state = not all_selected
                        for var, _ in checkboxes:
                            var.set(new_state)
                    return select_all_group

                group_items.sort(key=lambda x: x[0])
                for ticker, fp, dt_obj in group_items:
                    time_str = dt_obj.strftime('%H:%M:%S')
                    var = ctk.BooleanVar(value=False)
                    chk = ctk.CTkCheckBox(group_content, text=f"[{time_str}]  {ticker}",
                                          variable=var, font=("Consolas", 13), height=28, width=500)
                    chk.pack(anchor="w", padx=20, pady=1, fill="x")
                    file_vars.append((var, fp))
                    group_checkboxes.append((var, fp))
                btn_select_group.configure(command=create_group_select_all(group_checkboxes))

            if ungrouped_tickers:
                if grouped_tickers:
                    other_header = ctk.CTkFrame(scroll_frame, fg_color=("#3B3B3B", "#2B2B2B"), corner_radius=5)
                    other_header.pack(fill="x", padx=10, pady=(10, 2))
                    ctk.CTkLabel(other_header, text=f"其他 / Other ({len(ungrouped_tickers)} tickers)",
                                 font=("", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=5)
                ungrouped_tickers.sort(key=lambda x: x[0])
                for ticker, fp, dt_obj in ungrouped_tickers:
                    time_str = dt_obj.strftime('%H:%M:%S')
                    var = ctk.BooleanVar(value=False)
                    chk = ctk.CTkCheckBox(scroll_frame, text=f"[{time_str}]  {ticker}",
                                          variable=var, font=("Consolas", 14), height=30, width=500)
                    chk.pack(anchor="w", padx=10, pady=2, fill="x")
                    file_vars.append((var, fp))

        def load_files():
            try:
                date_str = cal.get_date()
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
                search_str = target_date.strftime("%Y%m%d")
            except Exception as e:
                import tkinter.messagebox
                tkinter.messagebox.showerror("Error", f"Invalid date: {e}")
                return

            grouped_files.clear()
            try:
                for root, dirs, files in os.walk(self.download_folder):
                    for file in files:
                        if search_str in file and file.endswith(('.html', '.txt', '.csv', '.pdf', '.png')):
                            fp = os.path.join(root, file)
                            try:
                                rel_path = os.path.relpath(fp, self.download_folder)
                                parts = rel_path.split(os.sep)
                                model_name = "Other"
                                ticker_name = file
                                if parts[0] == "CME":
                                    if len(parts) >= 3:
                                        model_name = f"CME - {parts[1]}"
                                        ticker_name = parts[2]
                                    elif "TV Code" in parts or file.lower().startswith("tv_codes"):
                                        model_name = "CME - TV Code"
                                        ticker_name = f"File_{file}"
                                else:
                                    if len(parts) >= 2:
                                        model_name = parts[0]
                                        ticker_name = parts[1]
                                    elif "TV Code" in parts or file.lower().startswith("tv_codes"):
                                        model_name = "TV Code"
                                        ticker_name = f"File_{file}"
                                try:
                                    time_part = file.split(search_str + "_")[1].split(".")[0]
                                    if len(time_part) >= 6:
                                        dt_time = datetime.strptime(time_part[:6], "%H%M%S")
                                    else:
                                        dt_time = datetime.now()
                                except Exception:
                                    mnow = os.path.getmtime(fp)
                                    dt_time = datetime.fromtimestamp(mnow)
                                if model_name not in grouped_files:
                                    grouped_files[model_name] = {}
                                if ticker_name not in grouped_files[model_name] or dt_time > grouped_files[model_name][ticker_name][1]:
                                    grouped_files[model_name][ticker_name] = (fp, dt_time)
                            except Exception:
                                pass
            except Exception as e:
                print(f"Error scanning files: {e}")

            total_files = sum(len(v) for v in grouped_files.values())
            lbl_status.configure(text=f"Found {total_files} files ({date_str})")
            sorted_models = sorted(grouped_files.keys())
            if not sorted_models:
                sorted_models = ["No Data"]
            seg_models.configure(values=sorted_models, command=lambda v: update_list(v))
            seg_models.set(sorted_models[0])
            update_list(sorted_models[0])

        btn_refresh = ctk.CTkButton(left_panel, text="Load / Refresh Files", width=180, height=35,
                                    font=("", 14, "bold"), fg_color="#3B8ED0", hover_color="#36719F",
                                    command=lambda: load_files())
        btn_refresh.pack(pady=(20, 10))
        lbl_status.pack(pady=5)

        btn_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))

        def select_all():
            for v, _ in file_vars:
                v.set(True)

        def deselect_all():
            for v, _ in file_vars:
                v.set(False)

        def open_selected():
            tv_data_to_show = []
            for v, data in file_vars:
                if v.get():
                    try:
                        if isinstance(data, tuple) and data[0] == "TV_DATA":
                            tv_data_to_show.append(data)
                        else:
                            self.open_file_cross_platform(data)
                    except Exception as e:
                        print(f"Error opening item: {e}")
            if tv_data_to_show:
                try:
                    import tempfile
                    fd, path = tempfile.mkstemp(prefix="TV_Selected_", suffix=".txt", text=True)
                    with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                        for _, t_label, content in tv_data_to_show:
                            clean_content = content
                            prefix = f"{t_label}:"
                            if clean_content.startswith(prefix):
                                clean_content = clean_content[len(prefix):].strip()
                            elif clean_content.startswith(t_label):
                                clean_content = clean_content[len(t_label):].strip()
                            tmp.write(f"{t_label}:\n\n")
                            tmp.write(f"{clean_content}\n\n")
                    self.open_file_cross_platform(path)
                except Exception as e:
                    print(f"Error creating aggregate TV file: {e}")

        ctk.CTkButton(btn_frame, text="Select All", command=select_all, width=120).pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="Deselect All", command=deselect_all, width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Open Selected", command=open_selected, width=150,
                      fg_color="#2CC985", hover_color="#229C68", text_color="white").pack(side="right", padx=20)

        # =====================================================
        # BY TICKER & MODEL: LEFT PANEL
        # =====================================================
        left_panel_bt = ctk.CTkFrame(window, width=300, corner_radius=0)
        left_panel_bt.grid_columnconfigure(0, weight=1)
        # Not gridded initially (hidden)

        ctk.CTkLabel(left_panel_bt, text="By Ticker & Model", font=("", 16, "bold"),
                     text_color="#DCE4EE").pack(pady=(15, 5))

        # --- Ticker Search ---
        ticker_section = ctk.CTkFrame(left_panel_bt, fg_color="transparent")
        ticker_section.pack(fill="x", padx=12, pady=(5, 0))
        ticker_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ticker_section, text="Ticker:", font=("", 13, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w", pady=(5, 2))

        bt_ticker_var = ctk.StringVar()
        bt_entry_ticker = ctk.CTkEntry(ticker_section, textvariable=bt_ticker_var,
                                       placeholder_text="Type to search...", height=32)
        bt_entry_ticker.grid(row=1, column=0, sticky="ew", pady=(0, 2))

        # Dropdown listbox
        bt_dropdown_frame = ctk.CTkFrame(ticker_section, fg_color=("#EBEBEB", "#2B2B2B"),
                                          corner_radius=5, border_width=1, border_color="gray")
        bt_listbox = tk.Listbox(bt_dropdown_frame, height=7, font=("Consolas", 12),
                                bg="#2B2B2B", fg="white", selectbackground="#3B8ED0",
                                selectforeground="white", borderwidth=0, highlightthickness=0,
                                activestyle="none")
        bt_listbox_scroll = tk.Scrollbar(bt_dropdown_frame, orient="vertical", command=bt_listbox.yview)
        bt_listbox.configure(yscrollcommand=bt_listbox_scroll.set)
        bt_listbox_scroll.pack(side="right", fill="y")
        bt_listbox.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        # bt_dropdown_frame is NOT gridded yet

        # Collect all tickers from both files
        all_tickers_std = []
        all_tickers_cme = []
        tickers_cme_set = set()
        if hasattr(self, 'ticker_filepath') and self.ticker_filepath and os.path.exists(self.ticker_filepath):
            std_groups = utils.load_tickers_with_groups(self.ticker_filepath)
            for grp, lst in std_groups.items():
                all_tickers_std.extend(lst)
        if hasattr(self, 'cme_ticker_filepath') and self.cme_ticker_filepath and os.path.exists(self.cme_ticker_filepath):
            cme_groups = utils.load_tickers_with_groups(self.cme_ticker_filepath)
            for grp, lst in cme_groups.items():
                all_tickers_cme.extend(lst)
                tickers_cme_set.update(lst)

        all_tickers_combined = sorted(set(all_tickers_std + all_tickers_cme))

        def bt_show_dropdown():
            bt_dropdown_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))

        def bt_hide_dropdown_now():
            bt_dropdown_frame.grid_remove()

        def bt_update_dropdown(event=None):
            query = bt_ticker_var.get().strip().upper()
            bt_listbox.delete(0, tk.END)
            matches = [t for t in all_tickers_combined if query in t.upper()] if query else all_tickers_combined
            for t in matches[:60]:
                bt_listbox.insert(tk.END, t)
            if matches:
                bt_show_dropdown()
            else:
                bt_hide_dropdown_now()

        def bt_select_ticker_from_list(event=None):
            sel = bt_listbox.curselection()
            if sel:
                ticker_val = bt_listbox.get(sel[0])
                bt_ticker_var.set(ticker_val)
                bt_hide_dropdown_now()
                bt_on_ticker_selected(ticker_val)
                bt_entry_ticker.focus_set()

        def bt_entry_on_focusout(event=None):
            def _maybe_hide():
                try:
                    fw = window.focus_get()
                    if fw is not bt_listbox:
                        bt_hide_dropdown_now()
                except Exception:
                    pass
            window.after(150, _maybe_hide)

        def bt_entry_on_down(event=None):
            if bt_listbox.size() > 0:
                bt_listbox.focus_set()
                bt_listbox.selection_clear(0, tk.END)
                bt_listbox.selection_set(0)
                bt_listbox.activate(0)

        def bt_entry_on_return(event=None):
            if bt_listbox.size() > 0:
                bt_listbox.selection_clear(0, tk.END)
                bt_listbox.selection_set(0)
                bt_select_ticker_from_list()

        bt_entry_ticker.bind("<KeyRelease>", bt_update_dropdown)
        bt_entry_ticker.bind("<FocusOut>", bt_entry_on_focusout)
        bt_entry_ticker.bind("<Escape>", lambda e: bt_hide_dropdown_now())
        bt_entry_ticker.bind("<Down>", bt_entry_on_down)
        bt_entry_ticker.bind("<Return>", bt_entry_on_return)
        bt_listbox.bind("<<ListboxSelect>>", bt_select_ticker_from_list)
        bt_listbox.bind("<Return>", bt_select_ticker_from_list)
        bt_listbox.bind("<Escape>", lambda e: (bt_hide_dropdown_now(), bt_entry_ticker.focus_set()))

        # --- Model Checkboxes ---
        model_section = ctk.CTkFrame(left_panel_bt, fg_color="transparent")
        model_section.pack(fill="x", padx=12, pady=(10, 0))
        model_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(model_section, text="Models:", font=("", 13, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w", pady=(4, 3))

        model_chk_frame = ctk.CTkFrame(model_section, fg_color=("#F0F0F0", "#2A2A2A"), corner_radius=6)
        model_chk_frame.grid(row=1, column=0, sticky="ew")
        model_chk_frame.grid_columnconfigure(0, weight=1)
        model_chk_frame.grid_columnconfigure(1, weight=1)

        _standard_models = ["Gamma", "Delta", "Theta", "Term", "Smile", "Levels", "Table", "TV Code"]
        _cme_models = ["Gamma", "Delta", "Smile", "Term", "TV Code"]

        bt_model_vars = {}

        def bt_rebuild_model_checkboxes(is_cme):
            for w in model_chk_frame.winfo_children():
                w.destroy()
            bt_model_vars.clear()
            models = _cme_models if is_cme else _standard_models
            for i, m in enumerate(models):
                var = ctk.BooleanVar(value=False)
                chk = ctk.CTkCheckBox(model_chk_frame, text=m, variable=var, font=("", 12))
                chk.grid(row=i // 2, column=i % 2, sticky="w", padx=10, pady=3)
                bt_model_vars[m] = var

        bt_rebuild_model_checkboxes(False)

        def bt_on_ticker_selected(ticker_val):
            is_cme = ticker_val in tickers_cme_set
            bt_rebuild_model_checkboxes(is_cme)

        # --- Date Range ---
        date_section = ctk.CTkFrame(left_panel_bt, fg_color="transparent")
        date_section.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(date_section, text="Date Range:", font=("", 13, "bold"), anchor="w").pack(
            fill="x", pady=(4, 3))

        def make_date_row(parent, label_text, default_date_str):
            row_frame = ctk.CTkFrame(parent, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(row_frame, text=label_text, width=46, font=("", 12), anchor="w").pack(side="left")
            dvar = ctk.StringVar(value=default_date_str)
            entry = ctk.CTkEntry(row_frame, textvariable=dvar, width=105, height=30,
                                 font=("Consolas", 12))
            entry.pack(side="left", padx=(2, 4))

            def open_cal_popup():
                popup = ctk.CTkToplevel(window)
                popup.title(label_text.strip())
                popup.geometry("310x270")
                popup.transient(window)
                popup.grab_set()
                popup.lift()
                popup.focus_force()
                try:
                    cur_val = datetime.strptime(dvar.get(), "%Y-%m-%d")
                except Exception:
                    cur_val = datetime.now()
                popup_cal = Calendar(popup, selectmode='day', date_pattern='yyyy-mm-dd',
                                     font=('Arial', 14), cursor="hand2")
                popup_cal.selection_set(cur_val)
                popup_cal.pack(padx=10, pady=10)

                def on_popup_select(e=None):
                    dvar.set(popup_cal.get_date())
                    popup.destroy()

                popup_cal.bind("<<CalendarSelected>>", on_popup_select)
                ctk.CTkButton(popup, text="OK", width=80, command=on_popup_select).pack(pady=(0, 8))

            btn_cal = ctk.CTkButton(row_frame, text="📅", width=32, height=30, font=("", 14),
                                    fg_color="transparent", border_width=1, border_color="gray",
                                    command=open_cal_popup)
            btn_cal.pack(side="left")
            return dvar

        _today_str = datetime.now().strftime("%Y-%m-%d")
        bt_start_date_var = make_date_row(date_section, "Start:", _today_str)
        bt_end_date_var = make_date_row(date_section, "End:  ", _today_str)

        # --- Search Button & Status ---
        bt_lbl_status = ctk.CTkLabel(left_panel_bt, text="Ready", font=("", 12), text_color="gray")
        bt_lbl_status.pack(pady=(10, 2))

        btn_bt_search = ctk.CTkButton(left_panel_bt, text="Search Files", width=180, height=35,
                                      font=("", 14, "bold"), fg_color="#3B8ED0", hover_color="#36719F",
                                      command=lambda: load_files_by_ticker())
        btn_bt_search.pack(pady=(2, 10))

        # =====================================================
        # BY TICKER & MODEL: RIGHT PANEL
        # =====================================================
        right_panel_bt = ctk.CTkFrame(window, fg_color="transparent")
        right_panel_bt.grid_rowconfigure(1, weight=1)
        right_panel_bt.grid_columnconfigure(0, weight=1)
        # Not gridded initially

        seg_bt_models = ctk.CTkSegmentedButton(right_panel_bt)
        seg_bt_models.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        bt_scroll_frame = ctk.CTkScrollableFrame(right_panel_bt)
        bt_scroll_frame.grid(row=1, column=0, sticky="nsew")

        bt_file_vars = []

        bt_btn_frame = ctk.CTkFrame(right_panel_bt, fg_color="transparent")
        bt_btn_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))

        def bt_select_all():
            for v, _ in bt_file_vars:
                v.set(True)

        def bt_deselect_all():
            for v, _ in bt_file_vars:
                v.set(False)

        def bt_open_selected():
            tv_data_to_show = []
            for v, data in bt_file_vars:
                if v.get():
                    try:
                        if isinstance(data, tuple) and data[0] == "TV_DATA":
                            tv_data_to_show.append(data)
                        else:
                            self.open_file_cross_platform(data)
                    except Exception as e:
                        print(f"Error opening item: {e}")
            if tv_data_to_show:
                try:
                    import tempfile
                    fd, path = tempfile.mkstemp(prefix="TV_Selected_", suffix=".txt", text=True)
                    with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                        for item in tv_data_to_show:
                            t_label = item[1]
                            content = item[2]
                            date_key = item[3] if len(item) > 3 else None
                            date_stamp = date_key.replace("-", "") if date_key else ""
                            clean_content = content
                            prefix = f"{t_label}:"
                            if clean_content.startswith(prefix):
                                clean_content = clean_content[len(prefix):].strip()
                            elif clean_content.startswith(t_label):
                                clean_content = clean_content[len(t_label):].strip()
                            header = f"{date_stamp} {t_label}:" if date_stamp else f"{t_label}:"
                            tmp.write(f"{header}\n\n")
                            tmp.write(f"{clean_content}\n\n")
                    self.open_file_cross_platform(path)
                except Exception as e:
                    print(f"Error creating aggregate TV file: {e}")

        ctk.CTkButton(bt_btn_frame, text="Select All", command=bt_select_all, width=120).pack(side="left", padx=20)
        ctk.CTkButton(bt_btn_frame, text="Deselect All", command=bt_deselect_all, width=120).pack(side="left", padx=5)
        ctk.CTkButton(bt_btn_frame, text="Open Selected", command=bt_open_selected, width=150,
                      fg_color="#2CC985", hover_color="#229C68", text_color="white").pack(side="right", padx=20)

        # --- By Ticker Scan Logic ---
        def load_files_by_ticker():
            import re as _re
            ticker = bt_ticker_var.get().strip()
            if not ticker:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Warning", "Please enter or select a ticker first.", parent=window)
                return

            selected_models = [m for m, var in bt_model_vars.items() if var.get()]
            if not selected_models:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Warning", "Please select at least one model.", parent=window)
                return

            try:
                start_date = datetime.strptime(bt_start_date_var.get().strip(), "%Y-%m-%d")
                end_date = datetime.strptime(bt_end_date_var.get().strip(), "%Y-%m-%d")
            except Exception as e:
                import tkinter.messagebox
                tkinter.messagebox.showerror("Error", f"Invalid date format (use YYYY-MM-DD): {e}", parent=window)
                return

            if start_date > end_date:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Warning", "Start date must be on or before end date.", parent=window)
                return

            is_cme = ticker in tickers_cme_set

            # date_key -> model_name -> ticker_name -> (fp, dt_time)
            bt_grouped = {}
            bt_lbl_status.configure(text="Scanning...")
            window.update_idletasks()

            try:
                for root, dirs, files in os.walk(self.download_folder):
                    for file in files:
                        if not file.endswith(('.html', '.txt', '.csv', '.pdf', '.png')):
                            continue
                        fp = os.path.join(root, file)
                        try:
                            rel_path = os.path.relpath(fp, self.download_folder)
                            parts = rel_path.split(os.sep)

                            model_name = "Other"
                            ticker_name = file

                            if parts[0] == "CME":
                                if len(parts) >= 3:
                                    model_name = f"CME - {parts[1]}"
                                    ticker_name = parts[2]
                                elif "TV Code" in parts or file.lower().startswith("tv_codes"):
                                    model_name = "CME - TV Code"
                                    ticker_name = f"File_{file}"
                            else:
                                if len(parts) >= 2:
                                    model_name = parts[0]
                                    ticker_name = parts[1]
                                elif "TV Code" in parts or file.lower().startswith("tv_codes"):
                                    model_name = "TV Code"
                                    ticker_name = f"File_{file}"

                            # Filter by CME vs standard
                            if is_cme:
                                if not model_name.startswith("CME - "):
                                    continue
                                raw_model = model_name[len("CME - "):]
                            else:
                                if model_name.startswith("CME - "):
                                    continue
                                raw_model = model_name

                            if raw_model not in selected_models:
                                continue

                            # For non-TV-Code, filter by ticker name
                            is_tv_code = "TV Code" in model_name
                            if not is_tv_code and ticker_name != ticker:
                                continue

                            # Extract date and time from filename
                            date_match = _re.search(r'(\d{8})_(\d{6})', file)
                            if not date_match:
                                continue
                            file_date_str = date_match.group(1)
                            time_str_raw = date_match.group(2)
                            try:
                                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                                file_dt = datetime.strptime(file_date_str + "_" + time_str_raw, "%Y%m%d_%H%M%S")
                            except Exception:
                                continue

                            if not (start_date <= file_date <= end_date):
                                continue

                            date_key = file_date.strftime("%Y-%m-%d")
                            if date_key not in bt_grouped:
                                bt_grouped[date_key] = {}
                            if model_name not in bt_grouped[date_key]:
                                bt_grouped[date_key][model_name] = {}

                            if is_tv_code:
                                # Keep all TV Code files (will be merged in display)
                                bt_grouped[date_key][model_name][f"File_{file}"] = (fp, file_dt)
                            else:
                                # Keep latest file per ticker per day
                                if (ticker_name not in bt_grouped[date_key][model_name] or
                                        file_dt > bt_grouped[date_key][model_name][ticker_name][1]):
                                    bt_grouped[date_key][model_name][ticker_name] = (fp, file_dt)

                        except Exception:
                            pass
            except Exception as e:
                print(f"Error scanning files: {e}")

            total = sum(len(t) for d in bt_grouped.values() for t in d.values())
            date_count = len(bt_grouped)
            bt_lbl_status.configure(text=f"Found {total} file(s) across {date_count} date(s)")
            update_list_by_ticker(bt_grouped, ticker, is_cme)

        def update_list_by_ticker(bt_grouped, ticker, is_cme):
            for widget in bt_scroll_frame.winfo_children():
                widget.destroy()
            bt_file_vars.clear()

            if not bt_grouped:
                seg_bt_models.configure(values=["No Data"], command=None)
                seg_bt_models.set("No Data")
                ctk.CTkLabel(bt_scroll_frame, text="No files found for the selected criteria.",
                             text_color="gray", font=("", 13)).pack(pady=60)
                return

            # Pivot: model_name -> date_key -> ticker_name -> (fp, dt_time)
            by_model = {}
            for date_key, models in bt_grouped.items():
                for model_name, tickers_map in models.items():
                    if model_name not in by_model:
                        by_model[model_name] = {}
                    by_model[model_name][date_key] = tickers_map

            def show_bt_model(selected_model):
                for widget in bt_scroll_frame.winfo_children():
                    widget.destroy()
                bt_file_vars.clear()

                if selected_model == "No Data" or selected_model not in by_model:
                    ctk.CTkLabel(bt_scroll_frame, text="No files found.", text_color="gray").pack(pady=50)
                    return

                dates_map = by_model[selected_model]
                is_tv = "TV Code" in selected_model

                for date_key in sorted(dates_map.keys()):
                    tickers_on_date = dates_map[date_key]

                    date_container = ctk.CTkFrame(bt_scroll_frame, fg_color="transparent")
                    date_container.pack(fill="x", padx=10, pady=(10, 5))

                    date_hdr = ctk.CTkFrame(date_container, fg_color=("#3B3B3B", "#2B2B2B"), corner_radius=5)
                    date_hdr.pack(fill="x", pady=(0, 2))
                    date_content = ctk.CTkFrame(date_container, fg_color="transparent")
                    date_content.pack(fill="x")

                    is_visible_date = ctk.BooleanVar(value=True)
                    date_chk_list = []

                    def make_date_toggle(dc, iv, tb):
                        def toggle():
                            if iv.get():
                                dc.pack_forget()
                                tb.configure(text=tb.cget("text").replace("▼", "▶"))
                                iv.set(False)
                            else:
                                dc.pack(fill="x")
                                tb.configure(text=tb.cget("text").replace("▶", "▼"))
                                iv.set(True)
                        return toggle

                    btn_sel_date = ctk.CTkButton(date_hdr, text="☑", width=30, height=28,
                                                 command=None, fg_color="transparent",
                                                 hover_color=("#4A4A4A", "#3A3A3A"), font=("", 16))
                    btn_sel_date.pack(side="left", padx=(5, 0), pady=5)

                    header_mid = ctk.CTkFrame(date_hdr, fg_color="transparent")
                    header_mid.pack(side="left", fill="x", expand=True)

                    n_date_label = "?" if is_tv else str(len(tickers_on_date))
                    toggle_date_btn = ctk.CTkButton(header_mid,
                                                    text=f"▼ {date_key}  ({n_date_label})",
                                                    command=None, fg_color="transparent",
                                                    hover_color=("#4A4A4A", "#3A3A3A"),
                                                    anchor="w", font=("", 13, "bold"))
                    toggle_date_btn.pack(side="left", fill="x", expand=True, padx=5, pady=5)
                    toggle_date_btn.configure(command=make_date_toggle(date_content, is_visible_date, toggle_date_btn))

                    if is_tv:
                        tv_files_sorted = sorted(tickers_on_date.values(), key=lambda x: x[1])
                        merged_tv = {}
                        for fp_tv, _ in tv_files_sorted:
                            try:
                                with open(fp_tv, "r", encoding="utf-8") as f:
                                    for line in f.readlines():
                                        line = line.strip()
                                        if not line:
                                            continue
                                        if '"' in line:
                                            pq = line.split('"')
                                            lbl = pq[1] if len(pq) > 1 else "Unknown"
                                        else:
                                            lbl = line.split(' ')[0].replace(":", "")
                                        merged_tv[lbl] = line
                            except Exception as e:
                                print(f"Error reading TV file: {e}")

                        filtered_tv = {lbl: c for lbl, c in merged_tv.items() if lbl == ticker}
                        toggle_date_btn.configure(text=f"▼ {date_key}  ({len(filtered_tv)})")

                        if not filtered_tv:
                            ctk.CTkLabel(date_content,
                                         text=f"  '{ticker}' not found in TV Code",
                                         text_color="gray", font=("", 12)).pack(anchor="w", padx=20, pady=4)
                        else:
                            for t_label, content in filtered_tv.items():
                                var = ctk.BooleanVar(value=True)
                                chk = ctk.CTkCheckBox(date_content, text=t_label, variable=var,
                                                      font=("Consolas", 13, "bold"))
                                chk.pack(anchor="w", padx=20, pady=2)
                                bt_file_vars.append((var, ("TV_DATA", t_label, content, date_key)))
                                date_chk_list.append((var, ("TV_DATA", t_label, content, date_key)))
                    else:
                        for tn, (fp_n, dt_obj) in sorted(tickers_on_date.items()):
                            time_s = dt_obj.strftime('%H:%M:%S')
                            var = ctk.BooleanVar(value=True)
                            chk = ctk.CTkCheckBox(date_content,
                                                  text=f"[{time_s}]  {tn}",
                                                  variable=var, font=("Consolas", 13), height=28, width=500)
                            chk.pack(anchor="w", padx=20, pady=1, fill="x")
                            bt_file_vars.append((var, fp_n))
                            date_chk_list.append((var, fp_n))

                    def make_date_sel_all(checkboxes):
                        def do_sel():
                            all_sel = all(v.get() for v, _ in checkboxes)
                            for v, _ in checkboxes:
                                v.set(not all_sel)
                        return do_sel

                    btn_sel_date.configure(command=make_date_sel_all(date_chk_list))

            sorted_models = sorted(by_model.keys())
            seg_bt_models.configure(values=sorted_models, command=show_bt_model)
            seg_bt_models.set(sorted_models[0])
            show_bt_model(sorted_models[0])

        # =====================================================
        # MODE SWITCH LOGIC
        # =====================================================
        def switch_mode(mode):
            if mode == "By Date":
                left_panel_bt.grid_remove()
                right_panel_bt.grid_remove()
                left_panel.grid(row=1, column=0, sticky="nsew")
                right_panel.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
            else:
                left_panel.grid_remove()
                right_panel.grid_remove()
                left_panel_bt.grid(row=1, column=0, sticky="nsew")
                right_panel_bt.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)

        seg_mode.configure(command=switch_mode)

        # Init: load By Date mode
        load_files()

    def open_file_cross_platform(self, filepath):
        import subprocess, sys, platform
        try:
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':       # macOS
                subprocess.call(('open', filepath))
            else:                                     # Linux
                subprocess.call(('xdg-open', filepath))
        except Exception as e:
            print(f"Failed to open file cross-platform: {e}")

    def open_ticker_manager_std(self):
        """Open ticker management window for Standard platform"""
        if not self.ticker_filepath:
            import tkinter.messagebox
            tkinter.messagebox.showwarning("警告", "請先選擇 Standard Ticker 檔案")
            return
        self.open_ticker_manager(self.ticker_filepath, "Standard Platform Tickers")
    
    def open_ticker_manager_cme(self):
        """Open ticker management window for CME platform"""
        if not self.cme_ticker_filepath:
            import tkinter.messagebox
            tkinter.messagebox.showwarning("警告", "請先選擇 CME Ticker 檔案")
            return
        self.open_ticker_manager(self.cme_ticker_filepath, "CME Platform Tickers")
    
    def open_ticker_manager(self, filepath, title):
        """
        Opens a window to manage tickers with groups
        """
        filepath = os.path.abspath(filepath)
        window = ctk.CTkToplevel(self)
        window.title(f"Manage Tickers - {title}")
        window.geometry("800x700")  # Increased height from 600 to 700
        window.transient(self)
        window.lift()
        window.focus_force()
        
        # Load current data
        groups_data = utils.load_tickers_with_groups(filepath)
        
        # Layout: Left (Group List) | Right (Ticker List + Controls)
        window.grid_columnconfigure(1, weight=1)
        window.grid_rowconfigure(0, weight=1)
        
        # === LEFT PANEL: Groups ===
        left_frame = ctk.CTkFrame(window, width=200)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(left_frame, text="群組 (Groups)", font=("", 16, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Group listbox
        group_frame = ctk.CTkScrollableFrame(left_frame)
        group_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        selected_group = ctk.StringVar(value="")
        group_buttons = []
        
        def refresh_groups():
            """Refresh the group list display"""
            for btn in group_buttons:
                btn.destroy()
            group_buttons.clear()
            
            for group_name in groups_data.keys():
                btn = ctk.CTkRadioButton(
                    group_frame, 
                    text=f"{group_name} ({len(groups_data[group_name])})",
                    variable=selected_group,
                    value=group_name,
                    command=refresh_tickers,
                    font=("", 13)
                )
                btn.pack(anchor="w", pady=2, padx=5)
                group_buttons.append(btn)
            
            # Only auto-select if there's no selection yet
            if groups_data and not selected_group.get():
                selected_group.set(list(groups_data.keys())[0])
                # Don't auto-refresh tickers here - let the initial call handle it
        
        # Group action buttons
        group_btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        group_btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        def add_group():
            dialog = ctk.CTkInputDialog(text="輸入新群組名稱:", title="新增群組")
            group_name = dialog.get_input()
            if group_name and group_name.strip():
                group_name = group_name.strip()
                if group_name in groups_data:
                    import tkinter.messagebox
                    tkinter.messagebox.showwarning("警告", "群組名稱已存在")
                else:
                    groups_data[group_name] = []
                    refresh_groups()
                    selected_group.set(group_name)
                    refresh_tickers()
        
        def rename_group():
            current = selected_group.get()
            if not current:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("警告", "請先選擇一個群組")
                return
            
            dialog = ctk.CTkInputDialog(text=f"重新命名群組 '{current}':", title="重新命名群組")
            new_name = dialog.get_input()
            if new_name and new_name.strip():
                new_name = new_name.strip()
                if new_name in groups_data and new_name != current:
                    import tkinter.messagebox
                    tkinter.messagebox.showwarning("警告", "群組名稱已存在")
                else:
                    groups_data[new_name] = groups_data.pop(current)
                    selected_group.set(new_name)
                    refresh_groups()
                    refresh_tickers()
        
        def delete_group():
            current = selected_group.get()
            if not current:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("警告", "請先選擇一個群組")
                return
            
            import tkinter.messagebox
            if tkinter.messagebox.askyesno("確認", f"確定要刪除群組 '{current}' 及其所有 tickers?"):
                del groups_data[current]
                selected_group.set("")
                refresh_groups()
                refresh_tickers()
        
        ctk.CTkButton(group_btn_frame, text="+ 新增", command=add_group, width=60, height=28).pack(side="left", padx=2)
        ctk.CTkButton(group_btn_frame, text="✏️ 重新命名", command=rename_group, width=80, height=28, fg_color="transparent", border_width=1).pack(side="left", padx=2)
        ctk.CTkButton(group_btn_frame, text="🗑️ 刪除", command=delete_group, width=60, height=28, fg_color="#FF4D4D", hover_color="#CC0000").pack(side="left", padx=2)
        
        # === RIGHT PANEL: Tickers ===
        right_frame = ctk.CTkFrame(window)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        
        ticker_label = ctk.CTkLabel(right_frame, text="Tickers", font=("", 16, "bold"))
        ticker_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Ticker listbox
        ticker_frame = ctk.CTkScrollableFrame(right_frame)
        ticker_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        ticker_frames = []  # Store only frame widgets
        ticker_checkboxes = {}  # ticker -> BooleanVar mapping
        
        def refresh_tickers():
            """Refresh the ticker list display"""
            # Clear checkboxes mapping first
            ticker_checkboxes.clear()
            
            # Destroy only frames (this will destroy their children automatically)
            for frame in ticker_frames:
                try:
                    frame.destroy()
                except:
                    pass  # Ignore errors if already destroyed
            ticker_frames.clear()
            
            current_group = selected_group.get()
            ticker_label.configure(text=f"Tickers - {current_group}" if current_group else "Tickers")
            
            if not current_group or current_group not in groups_data:
                return
            
            tickers = groups_data[current_group]
            for ticker in tickers:
                frame = ctk.CTkFrame(ticker_frame, fg_color="transparent")
                frame.pack(fill="x", pady=2, padx=5)
                ticker_frames.append(frame)  # Only store the frame
                
                # Checkbox for selection
                var = ctk.BooleanVar(value=False)
                ticker_checkboxes[ticker] = var
                
                chk = ctk.CTkCheckBox(frame, text=ticker, variable=var, font=("", 14))
                chk.pack(side="left", fill="x", expand=True, padx=5)
                
                # Delete button
                def make_delete_handler(t):
                    return lambda: delete_ticker(t)
                
                btn_del = ctk.CTkButton(frame, text="🗑️", width=30, height=24, 
                                       command=make_delete_handler(ticker),
                                       fg_color="#FF4D4D", hover_color="#CC0000")
                btn_del.pack(side="right", padx=2)

        
        def add_ticker():
            current_group = selected_group.get()
            if not current_group:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("警告", "請先選擇一個群組")
                return
            
            dialog = ctk.CTkInputDialog(text="輸入 Ticker 代號 (多個請用逗號分隔):", title="新增 Ticker")
            ticker_input = dialog.get_input()
            if ticker_input and ticker_input.strip():
                new_tickers = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]
                for ticker in new_tickers:
                    if ticker not in groups_data[current_group]:
                        groups_data[current_group].append(ticker)
                refresh_groups()
                refresh_tickers()
        
        def move_ticker(ticker):
            """Move ticker(s) to another group. Supports single ticker (string) or multiple tickers (list)"""
            current_group = selected_group.get()
            
            # Handle both single ticker and list of tickers
            if isinstance(ticker, list):
                tickers_to_move = ticker
                ticker_display = f"{len(tickers_to_move)} 個 tickers"
            else:
                tickers_to_move = [ticker]
                ticker_display = f"'{ticker}'"
            
            # Validate all tickers are in current group
            if not current_group:
                return
            
            valid_tickers = [t for t in tickers_to_move if t in groups_data[current_group]]
            if not valid_tickers:
                return
            
            # Get available target groups (exclude current group)
            target_groups = [g for g in groups_data.keys() if g != current_group]
            
            if not target_groups:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("警告", "沒有其他群組可以移動。請先建立新群組。")
                return
            
            # Create selection dialog
            move_window = ctk.CTkToplevel(window)
            move_window.title(f"批次移動 Tickers")
            move_window.geometry("400x450")  # Increased from 280 to 450
            move_window.transient(window)
            move_window.lift()
            move_window.focus_force()
            
            ctk.CTkLabel(move_window, text=f"選擇目標群組:", font=("", 14, "bold")).pack(pady=15, padx=20)
            ctk.CTkLabel(move_window, text=f"將 {ticker_display} 從 '{current_group}' 移動到:", font=("", 12)).pack(pady=5, padx=20)
            
            # Group selection
            selected_target = ctk.StringVar(value=target_groups[0])
            
            group_select_frame = ctk.CTkScrollableFrame(move_window, height=200)  # Increased from 120 to 200
            group_select_frame.pack(fill="x", padx=20, pady=10)
            
            for target_group in sorted(target_groups):
                rb = ctk.CTkRadioButton(
                    group_select_frame,
                    text=f"{target_group} ({len(groups_data[target_group])} tickers)",
                    variable=selected_target,
                    value=target_group,
                    font=("", 12)
                )
                rb.pack(anchor="w", pady=2, padx=5)
            
            # Buttons
            btn_frame = ctk.CTkFrame(move_window, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            def confirm_move():
                target = selected_target.get()
                if target and target in groups_data:
                    # Move all valid tickers
                    for t in valid_tickers:
                        # Remove from current group
                        groups_data[current_group].remove(t)
                        
                        # Add to target group (avoid duplicates)
                        if t not in groups_data[target]:
                            groups_data[target].append(t)
                    
                    refresh_groups()
                    refresh_tickers()
                    move_window.destroy()
            
            def cancel_move():
                move_window.destroy()
            
            ctk.CTkButton(btn_frame, text="✓ 確認移動", command=confirm_move, width=120, 
                         fg_color="#2CC985", hover_color="#229C68").pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="✖ 取消", command=cancel_move, width=120,
                         fg_color="gray", hover_color="darkgray").pack(side="left", padx=5)
        
        def delete_ticker(ticker):
            current_group = selected_group.get()
            if current_group and ticker in groups_data[current_group]:
                groups_data[current_group].remove(ticker)
                refresh_groups()
                refresh_tickers()
        
        # Ticker action buttons
        ticker_btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        ticker_btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        def select_all_tickers():
            """Select all tickers in current group"""
            for var in ticker_checkboxes.values():
                var.set(True)
        
        def deselect_all_tickers():
            """Deselect all tickers in current group"""
            for var in ticker_checkboxes.values():
                var.set(False)
        
        def batch_move_tickers():
            """Move selected tickers to another group"""
            current_group = selected_group.get()
            if not current_group:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("警告", "請先選擇一個群組")
                return
            
            # Get selected tickers
            selected_tickers = [ticker for ticker, var in ticker_checkboxes.items() if var.get()]
            
            if not selected_tickers:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("警告", "請先勾選要移動的 tickers")
                return
            
            # Call move_ticker with list of tickers
            move_ticker(selected_tickers)
        
        ctk.CTkButton(ticker_btn_frame, text="+ 新增 Ticker", command=add_ticker, width=100, height=32).pack(side="left", padx=5)
        ctk.CTkButton(ticker_btn_frame, text="☑ 全選", command=select_all_tickers, width=70, height=32, fg_color="transparent", border_width=1).pack(side="left", padx=2)
        ctk.CTkButton(ticker_btn_frame, text="☐ 取消", command=deselect_all_tickers, width=70, height=32, fg_color="transparent", border_width=1).pack(side="left", padx=2)
        ctk.CTkButton(ticker_btn_frame, text="➜ 批次移動", command=batch_move_tickers, width=100, height=32, fg_color="#3B8ED0", hover_color="#36719F").pack(side="left", padx=5)
        
        # === BOTTOM: Save/Cancel ===
        bottom_frame = ctk.CTkFrame(window, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        
        def save_changes():
            if utils.save_tickers_with_groups(filepath, groups_data):
                self.log(f"Ticker 檔案已儲存: {filepath}")
                import tkinter.messagebox
                tkinter.messagebox.showinfo("成功", "變更已儲存")
                window.destroy()
            else:
                import tkinter.messagebox
                tkinter.messagebox.showerror("錯誤", "儲存失敗")
        
        def cancel_changes():
            window.destroy()
        
        ctk.CTkButton(bottom_frame, text="💾 儲存", command=save_changes, width=120, height=35, 
                     fg_color="#2CC985", hover_color="#229C68", font=("", 13, "bold")).pack(side="right", padx=5)
        ctk.CTkButton(bottom_frame, text="✖️ 取消", command=cancel_changes, width=120, height=35,
                     fg_color="gray", hover_color="darkgray", font=("", 13, "bold")).pack(side="right", padx=5)
        
        # Initial load
        refresh_groups()
        # Manually refresh tickers for the initially selected group
        if selected_group.get():
            refresh_tickers()

    def close_app(self):
        try:
            self.save_settings()
        except:
            pass
        self.destroy()

# Override init to load settings and protocol close
# We need to inject this into __init__ or just call it after creation in main.py? 
# Better: call in __init__
