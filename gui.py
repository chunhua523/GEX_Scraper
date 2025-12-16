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

        # Row 2: View Files Button (New)
        self.btn_view_files = ctk.CTkButton(self.global_frame, text="📂 View Today's Files", command=self.open_file_viewer, width=180)
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
            
    def open_file_viewer(self):
        """
        Opens a Toplevel window to list and open files downloaded today.
        Optimized with filename string matching and SegmentedButton for model selection.
        """
        if not hasattr(self, 'download_folder') or not self.download_folder or not os.path.exists(self.download_folder):
            import tkinter.messagebox
            tkinter.messagebox.showwarning("Warning", "Download folder is not set or invalid.")
            return

        # Create Window
        window = ctk.CTkToplevel(self)
        window.title("Today's Downloaded Files")
        window.geometry("700x600")
        window.attributes("-topmost", True) # Keep on top

        # Fast Filtering: Use datestring in filename instead of os.stat
        today_str = datetime.now().strftime("%Y%m%d")
        
        # Grouping: grouped_files[model_name] = { ticker_name: (filepath, time_obj) }
        grouped_files = {} 
        files_found_count = 0

        try:
            for root, dirs, files in os.walk(self.download_folder):
                 for file in files:
                      # Check if file has today's date string (Fastest check)
                      if today_str in file and file.endswith(('.html', '.txt', '.csv', '.pdf', '.png')):
                          fp = os.path.join(root, file)
                          
                          try:
                                # Parsing structure
                                rel_path = os.path.relpath(fp, self.download_folder)
                                parts = rel_path.split(os.sep)
                                
                                model_name = "Other"
                                ticker_name = file # Default
                                
                                # Heuristics
                                if parts[0] == "CME":
                                    if len(parts) >= 3:
                                        model_name = f"CME - {parts[1]}"
                                        ticker_name = parts[2]
                                    elif "TV Code" in parts or file.lower().startswith("tv_codes"):
                                        model_name = "CME - TV Code"
                                        ticker_name = f"File_{file}" # Unique key to keep all files
                                else:
                                    if len(parts) >= 2:
                                        model_name = parts[0]
                                        ticker_name = parts[1]
                                    elif "TV Code" in parts or file.lower().startswith("tv_codes"): # Standard TV Code
                                        model_name = "TV Code"
                                        ticker_name = f"File_{file}"

                                # Extract time from filename for sorting? 
                                # Filename format: ..._YYYYMMDD_HHMMSS.ext
                                # Regex extract HHMMSS
                                try:
                                    time_part = file.split(today_str + "_")[1].split(".")[0]
                                    # Basic check if it looks like time
                                    if len(time_part) >= 6:
                                        dt_time = datetime.strptime(time_part[:6], "%H%M%S")
                                    else:
                                        dt_time = datetime.now() # Fallback
                                except:
                                    # Fallback to mtime if regex fails (slower but rare)
                                    mnow = os.path.getmtime(fp)
                                    dt_time = datetime.fromtimestamp(mnow)
                                
                                if model_name not in grouped_files:
                                    grouped_files[model_name] = {}
                                
                                # Keep latest file for this ticker
                                if ticker_name not in grouped_files[model_name] or dt_time > grouped_files[model_name][ticker_name][1]:
                                    grouped_files[model_name][ticker_name] = (fp, dt_time)
                                    
                          except Exception:
                              pass
        except Exception as e:
            self.log_safe(f"Error scanning files: {e}")

        # Flatten for count
        total_files = sum(len(v) for v in grouped_files.values())
        
        # Sort models
        sorted_models = sorted(grouped_files.keys())
        if not sorted_models:
             sorted_models = ["No Data"]

        # --- UI UI UI ---
        
        # 1. Top Bar: Model Selector (Segmented Button)
        top_frame = ctk.CTkFrame(window, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(top_frame, text=f"Found {total_files} files (Today)", font=("", 14, "bold")).pack(anchor="w", padx=5)

        # Segmented Button
        # Logic: If too many models, might look crowded. But usually ~5-10 models max.
        self.seg_models = ctk.CTkSegmentedButton(top_frame, values=sorted_models, command=lambda v: update_list(v))
        self.seg_models.pack(pady=10, fill="x")
        if sorted_models[0] != "No Data":
            self.seg_models.set(sorted_models[0]) # Select first

        # 2. List Area
        scroll_frame = ctk.CTkScrollableFrame(window, width=640, height=400)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        file_vars = [] # (BooleanVar, filepath)

        def update_list(selected_model):
            # Clear existing
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            file_vars.clear()
            
            if selected_model == "No Data" or selected_model not in grouped_files:
                ctk.CTkLabel(scroll_frame, text="No files found.", text_color="gray").pack(pady=50)
                return

            tickers = grouped_files[selected_model]
            
            # Special Handling for TV Code categories
            if "TV Code" in selected_model:
                # 1. Collect all files and sort by time (Oldest -> Newest) so latest overwrites earlier
                tv_files = []
                for file_key in tickers:
                    fp, dt_obj = tickers[file_key]
                    tv_files.append((dt_obj, fp))
                
                tv_files.sort(key=lambda x: x[0]) # Sort by datetime ascending

                merged_tv_items = {} # ticker -> content (Last one wins)

                try:
                    for _, fp in tv_files:
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            
                            for line in lines:
                                line = line.strip()
                                if not line: continue
                                
                                # Heuristic to extract Ticker
                                ticker_label = "Unknown"
                                if '"' in line:
                                    parts_q = line.split('"')
                                    if len(parts_q) > 1:
                                        ticker_label = parts_q[1]
                                else:
                                    # Fallback: First word
                                    ticker_label = line.split(' ')[0].replace(":", "")
                                
                                merged_tv_items[ticker_label] = line
                        except Exception as e:
                            print(f"Error reading {fp}: {e}")

                    if not merged_tv_items:
                         ctk.CTkLabel(scroll_frame, text="No content found in TV Code files.", text_color="gray").pack(pady=20)

                    # Display Unique Tickers (Sorted)
                    for t_label in sorted(merged_tv_items.keys()):
                        content = merged_tv_items[t_label]
                        var = ctk.BooleanVar(value=False)
                        
                        # Container (Compact: just the checkbox line)
                        # chk = ctk.CTkCheckBox(scroll_frame, text=f"{t_label}", variable=var, font=("", 14, "bold"), width=100)
                        # chk.pack(anchor="w", padx=20, pady=2, fill="x")

                        # Using a Frame to keep alignment consistent if we add more info later, but for now just Checkbox is fine.
                        # Actually let's use the frame for margin consistecy with previous code style
                        item_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                        item_frame.pack(fill="x", pady=2)

                        chk = ctk.CTkCheckBox(item_frame, text=f"{t_label}", variable=var, font=("Consolas", 14, "bold"), width=100)
                        chk.pack(anchor="w", padx=10)

                        file_vars.append((var, ("TV_DATA", t_label, content)))
                        
                except Exception as e:
                     ctk.CTkLabel(scroll_frame, text=f"Error processing TV Code files: {e}", text_color="red").pack(pady=10)
                return

            # Normal Files
            # Sort by Ticker Name
            for ticker in sorted(tickers.keys()):
                fp, dt_obj = tickers[ticker]
                time_str = dt_obj.strftime('%H:%M:%S')
                
                var = ctk.BooleanVar(value=False)
                
                # Simple clean format
                chk = ctk.CTkCheckBox(scroll_frame, text=f"[{time_str}]  {ticker}", variable=var, font=("Consolas", 14), height=30, width=500)
                chk.pack(anchor="w", padx=10, pady=2, fill="x")
                file_vars.append((var, fp))

        # 3. Bottom Actions
        btn_frame = ctk.CTkFrame(window, fg_color="transparent")
        btn_frame.pack(pady=15, fill="x")

        def select_all():
             for v, _ in file_vars: v.set(True)

        def deselect_all():
             for v, _ in file_vars: v.set(False)

        def open_selected():
            tv_data_to_show = []
            
            for v, data in file_vars:
                if v.get():
                    try:
                        if isinstance(data, tuple) and data[0] == "TV_DATA":
                            # Collect TV Data for aggregation
                            tv_data_to_show.append(data)
                        else:
                            # Normal file path - open immediately
                            os.startfile(data)
                    except Exception as e:
                        print(f"Error opening item: {e}")
            
            # Handle aggregated TV Data
            if tv_data_to_show:
                try:
                    import tempfile
                    # Create one single temp file for all selected tickers
                    fd, path = tempfile.mkstemp(prefix=f"TV_Selected_", suffix=".txt", text=True)
                    
                    with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                        for _, t_label, content in tv_data_to_show:
                            # Clean content: Remove "Ticker:" prefix if it exists to avoid redundancy
                            # content is the raw line, e.g. "AAOI: Put Dominate..."
                            clean_content = content
                            prefix = f"{t_label}:"
                            if clean_content.startswith(prefix):
                                clean_content = clean_content[len(prefix):].strip()
                            elif clean_content.startswith(t_label): # Just ticker space?
                                clean_content = clean_content[len(t_label):].strip()
                            
                            # Format:
                            # AAOI:
                            # 
                            # Put Dominate...
                            # 
                            
                            tmp.write(f"{t_label}:\n\n")
                            tmp.write(f"{clean_content}\n\n")
                            
                    os.startfile(path)
                except Exception as e:
                    print(f"Error creating aggregate TV file: {e}")

        ctk.CTkButton(btn_frame, text="Select All", command=select_all, width=120).pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="Deselect All", command=deselect_all, width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Open Selected", command=open_selected, width=150, fg_color="#2CC985", hover_color="#229C68", text_color="white").pack(side="right", padx=20)

        # Init list
        if sorted_models[0] != "No Data":
            update_list(sorted_models[0])

    def close_app(self):
        try:
            self.save_settings()
        except:
            pass
        self.destroy()

# Override init to load settings and protocol close
# We need to inject this into __init__ or just call it after creation in main.py? 
# Better: call in __init__
