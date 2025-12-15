import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading
import asyncio
import os
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
    
    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Lieta Scraper", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

    def create_main_area(self):
        # Use ScrollableFrame to prevent cutting off elements when window is small
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        # self.main_frame.grid_rowconfigure(3, weight=1) # No longer needed with scrollable frame
        
        # 1. Login / Status Section
        self.status_frame = ctk.CTkFrame(self.main_frame)
        self.status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_login = ctk.CTkButton(self.status_frame, text="Log in via Browser", command=self.on_login_click)
        self.btn_login.pack(side="left", padx=10, pady=10)
        
        self.lbl_login_status = ctk.CTkLabel(self.status_frame, text="Not Logged In", text_color="red")
        self.lbl_login_status.pack(side="left", padx=10)

        # 2. Configuration Section
        self.config_frame = ctk.CTkFrame(self.main_frame)
        self.config_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        
        # --- Standard Platform ---
        ctk.CTkLabel(self.config_frame, text="[Standard Platform]", font=("", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="w")

        # Ticker File
        self.btn_ticker_file = ctk.CTkButton(self.config_frame, text="Select Ticker List", command=self.select_ticker_file)
        self.btn_ticker_file.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.lbl_ticker_file = ctk.CTkLabel(self.config_frame, text="No file selected")
        self.lbl_ticker_file.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # --- CME Platform ---
        ctk.CTkLabel(self.config_frame, text="[CME Platform]", font=("", 14, "bold")).grid(row=2, column=0, columnspan=2, pady=(15, 5), sticky="w")

        # CME Ticker File
        self.btn_cme_ticker = ctk.CTkButton(self.config_frame, text="Select CME Ticker List", command=self.select_cme_ticker_file)
        self.btn_cme_ticker.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.lbl_cme_ticker = ctk.CTkLabel(self.config_frame, text="No file selected")
        self.lbl_cme_ticker.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # Global Download Path
        ctk.CTkLabel(self.config_frame, text="[Global Configuration]", font=("", 14, "bold")).grid(row=4, column=0, columnspan=2, pady=(15, 5), sticky="w")
        
        self.btn_dl_path = ctk.CTkButton(self.config_frame, text="Select Download Folder", command=self.select_download_path)
        self.btn_dl_path.grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.lbl_dl_path = ctk.CTkLabel(self.config_frame, text="No folder selected")
        self.lbl_dl_path.grid(row=5, column=1, padx=10, pady=10, sticky="w")

        # 3. Model Selection & Options
        self.options_frame = ctk.CTkFrame(self.main_frame)
        self.options_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        # Standard Models
        ctk.CTkLabel(self.options_frame, text="Standard Models:").pack(anchor="w", padx=10, pady=5)
        self.scroll_models = ctk.CTkScrollableFrame(self.options_frame, height=120)
        self.scroll_models.pack(fill="x", padx=10, pady=5)
        
        self.model_vars = {}
        standard_models = ["Gamma", "Delta", "Theta", "Term", "Smile", "Levels", "Table", "TV Code"] 
        for model in standard_models:
            var = ctk.StringVar(value="off")
            chk = ctk.CTkCheckBox(self.scroll_models, text=model, variable=var, onvalue=model, offvalue="off")
            chk.pack(anchor="w", pady=2)
            self.model_vars[model] = var

        # CME Models
        ctk.CTkLabel(self.options_frame, text="CME Models:").pack(anchor="w", padx=10, pady=5)
        self.scroll_cme_models = ctk.CTkScrollableFrame(self.options_frame, height=100)
        self.scroll_cme_models.pack(fill="x", padx=10, pady=5)
        
        self.cme_model_vars = {}
        cme_models = ["Gamma", "Delta", "Smile", "Term", "TV Code"]
        for model in cme_models:
            var = ctk.StringVar(value="off")
            chk = ctk.CTkCheckBox(self.scroll_cme_models, text=model, variable=var, onvalue=model, offvalue="off")
            chk.pack(anchor="w", pady=2)
            self.cme_model_vars[model] = var

        # Parallel Execution
        self.var_parallel = ctk.BooleanVar(value=False)
        self.chk_parallel = ctk.CTkSwitch(self.options_frame, text="Multi-window Mode (Parallel Download)", variable=self.var_parallel)
        self.chk_parallel.pack(anchor="w", padx=10, pady=10)

        # 4. Action Buttons
        self.action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_start = ctk.CTkButton(self.action_frame, text="Start Scraping", fg_color="green", command=self.on_start)
        self.btn_start.pack(side="left", padx=10, expand=True, fill="x")
        
        self.btn_stop = ctk.CTkButton(self.action_frame, text="Stop", fg_color="red", state="disabled", command=self.on_stop)
        self.btn_stop.pack(side="right", padx=10, expand=True, fill="x")

        # 5. Console
        self.console_label = ctk.CTkLabel(self.main_frame, text="Logs:")
        self.console_label.grid(row=4, column=0, sticky="w", padx=20)
        
        self.console = ctk.CTkTextbox(self.main_frame, height=150)
        self.console.grid(row=5, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # State variables
        self.ticker_filepath = None
        self.cme_ticker_filepath = None
        self.download_folder = None
    
    
    def on_login_click(self):
        self.btn_login.configure(state="disabled")
        self.log("Initializing Login Browser...")
        threading.Thread(target=self._run_login_thread, daemon=True).start()

    def _run_login_thread(self):
        try:
            # Create a new scraper instance for login or reuse?
            # Better to reuse internal browser state mechanism.
            # We'll create a scraper instance just for this action or keep a shared one?
            # Shared one is better if we want to keep browser open, but here we save state to disk.
            # So ad-hoc instance is fine.
            # So ad-hoc instance is fine.
            scraper = LietaScraper(logger_func=self.log_safe)
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

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log(f"Starting job... (Std: {len(tickers)} tickers, CME: {len(cme_tickers)} tickers)")
        
        threading.Thread(target=self._run_job_thread, args=(tickers, selected_models, cme_tickers, selected_cme_models, self.download_folder, parallel), daemon=True).start()

    def _run_job_thread(self, tickers, models, cme_tickers, cme_models, download_folder, parallel):
        self.scraper_instance = LietaScraper(logger_func=self.log_safe)
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
            "parallel": self.var_parallel.get()
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
                
        except Exception as e:
            print(f"Failed to load settings: {e}")
            
    def close_app(self):
        self.save_settings()
        self.destroy()

# Override init to load settings and protocol close
# We need to inject this into __init__ or just call it after creation in main.py? 
# Better: call in __init__
