import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading
import asyncio
import os
from datetime import datetime
from scraper import LietaScraper
import utils
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
                        self.on_start()
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
        self.std_ticker_row.pack(padx=0, pady=5, fill="x", anchor="w")
        
        self.btn_ticker_file = ctk.CTkButton(self.std_ticker_row, text="Select Ticker List", command=self.select_ticker_file, width=140)
        self.btn_ticker_file.grid(row=0, column=0, padx=15, sticky="w")
        self.lbl_ticker_file = ctk.CTkLabel(self.std_ticker_row, text="No file selected", font=("", 12), text_color="#DCE4EE")
        self.lbl_ticker_file.grid(row=0, column=1, padx=5, sticky="w")

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
        self.cme_ticker_row.pack(padx=0, pady=5, fill="x", anchor="w")

        self.btn_cme_ticker = ctk.CTkButton(self.cme_ticker_row, text="Select CME Ticker List", command=self.select_cme_ticker_file, width=140)
        self.btn_cme_ticker.grid(row=0, column=0, padx=15, sticky="w")
        self.lbl_cme_ticker = ctk.CTkLabel(self.cme_ticker_row, text="No file selected", font=("", 12), text_color="#DCE4EE")
        self.lbl_cme_ticker.grid(row=0, column=1, padx=5, sticky="w")

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

        # Row 2: Parallel Switch (Separate Line)
        self.var_parallel = ctk.BooleanVar(value=False)
        self.chk_parallel = ctk.CTkSwitch(self.global_frame, text="Multi-window Mode (Scrape Std & CME in parallel)", variable=self.var_parallel)
        self.chk_parallel.grid(row=2, column=0, columnspan=2, padx=15, pady=5, sticky="w")

        # Row 3: Schedule Section (Separate Line with background)
        self.schedule_subframe = ctk.CTkFrame(self.global_frame, fg_color="transparent")
        self.schedule_subframe.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(5, 15))
        
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

        # 6. Console
        self.console_label = ctk.CTkLabel(self.main_frame, text="Logs:")
        self.console_label.grid(row=5, column=0, sticky="w", padx=20)
        
        self.console = ctk.CTkTextbox(self.main_frame, height=150)
        self.console.grid(row=6, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
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
            self.ticker_filepath = path
            self.lbl_ticker_file.configure(text=os.path.basename(path))
            self.log(f"Selected tickers: {path}")

    def select_cme_ticker_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text/CSV", "*.txt *.csv")])
        if path:
            self.cme_ticker_filepath = path
            self.lbl_cme_ticker.configure(text=os.path.basename(path))
            self.log(f"Selected CME tickers: {path}")

    def select_download_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_folder = path
            self.lbl_dl_path.configure(text=path)
            self.log(f"Selected download folder: {path}")

    def on_start(self):
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
            tickers = utils.load_tickers_from_file(self.ticker_filepath)
        
        if selected_cme_models:
            if not self.cme_ticker_filepath:
                self.log("Error: CME models selected but no CME Ticker list provided.")
                return
            cme_tickers = utils.load_tickers_from_file(self.cme_ticker_filepath)
            
        if not selected_models and not selected_cme_models:
            self.log("Error: Please select at least one model (Standard or CME).")
            return

        parallel = self.var_parallel.get()
        browser_type = self.var_browser.get()

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        # Setup Logger for this run
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = os.path.join("logs", f"run_{timestamp}.log")
        self.log(f"Starting job... (Std: {len(tickers)} tickers, CME: {len(cme_tickers)} tickers) Browser: {browser_type}")
        self.log(f"Logging to: {self.current_log_file}")
        
        threading.Thread(target=self._run_job_thread, args=(tickers, selected_models, cme_tickers, selected_cme_models, self.download_folder, parallel, browser_type), daemon=True).start()

    def _run_job_thread(self, tickers, models, cme_tickers, cme_models, download_folder, parallel, browser_type):
        self.scraper_instance = LietaScraper(logger_func=self.log_safe, browser_type=browser_type)
        try:
            # Fix: Run everything in one asyncio loop to preserve browser connection
            asyncio.run(self.scraper_instance.perform_full_job(tickers, models, cme_tickers, cme_models, download_folder, parallel))
        except Exception as e:
            self.log_safe(f"Job Critical Error: {e}")
        finally:
            self.scraper_instance = None
            self.after(0, self._job_finished)

    def _job_finished(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.log("Ready.")
        self.current_log_file = None

    
    def on_stop(self):
        if hasattr(self, 'scraper_instance') and self.scraper_instance:
            self.log("Blocking new requests. Stopping...")
            self.scraper_instance.stop_requested = True
            # Forcing thread stop or asyncio cancel is hard from outside.
            # Best way: Check stop_requested flag in scraper logic.
            
            # If we were using proper asyncio loop integration in GUI we could cancel task.
            # With threading, we rely on the flag check inside scraper logic.


    def log(self, message):
        self.console.insert("end", message + "\n")
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
            "ticker_filepath": self.ticker_filepath,
            "cme_ticker_filepath": self.cme_ticker_filepath,
            "download_folder": self.download_folder,
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
                self.ticker_filepath = settings["ticker_filepath"]
                self.lbl_ticker_file.configure(text=os.path.basename(self.ticker_filepath))
            
            if settings.get("cme_ticker_filepath"):
                self.cme_ticker_filepath = settings["cme_ticker_filepath"]
                self.lbl_cme_ticker.configure(text=os.path.basename(self.cme_ticker_filepath))
            
            if settings.get("download_folder"):
                self.download_folder = settings["download_folder"]
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
            
    def close_app(self):
        self.save_settings()
        self.destroy()

# Override init to load settings and protocol close
# We need to inject this into __init__ or just call it after creation in main.py? 
# Better: call in __init__
