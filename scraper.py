import asyncio
import os
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import utils

# URL
BASE_URL = "https://www.lietaresearch.com"

class LietaScraper:
    def __init__(self, logger_func=print, browser_type="chrome"):
        self.log = logger_func
        self.playwright = None
        self.browser = None
        self.storage_state_path = "state.json"
        self.browser_type = browser_type
        
        self.stop_requested = False # Flag to control stopping

    def _get_brave_path(self):
        """Attempts to find Brave Browser executable path."""
        import platform
        system = platform.system()
        
        if system == "Windows":
            paths = [
                os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "BraveSoftware\\Brave-Browser\\Application\\brave.exe")
            ]
            for p in paths:
                if os.path.exists(p):
                    return p
        elif system == "Darwin": # macOS
            path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            if os.path.exists(path):
                return path
        
        return None

    async def start_browser(self, headless=False):
        self.playwright = await async_playwright().start()
        
        launch_args = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled"]
        }

        if self.browser_type == "brave":
            brave_path = self._get_brave_path()
            if brave_path:
                launch_args["executable_path"] = brave_path
                self.log(f"Verified Brave path: {brave_path}")
            else:
                self.log("Brave not found, falling back to System Chrome...")
                launch_args["channel"] = "chrome"
        else:
            # Default to Chrome
            launch_args["channel"] = "chrome"

        self.browser = await self.playwright.chromium.launch(**launch_args)
        self.log(f"Browser launched ({self.browser_type}).")

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.log("Browser closed.")

    async def ensure_login(self):
        """
        Opens browser, checks if logged in. If not, waits for user to log in.
        Saves state to storage_state_path.
        """
        # Load existing state if available
        context_args = {}
        if os.path.exists(self.storage_state_path):
            context_args["storage_state"] = self.storage_state_path
            self.log("Found existing session state.")

        context = await self.browser.new_context(**context_args)
        page = await context.new_page()
        
        try:
            self.log(f"Navigating to {BASE_URL}...")
            await page.goto(BASE_URL)
            
            # Check for login indicator. 
            # Looking at screenshot: There is a Profile Icon (green circle with person).
            # We assume if that exists, we are logged in.
            # If we see a "Login" or "Sign In" button, we are not.
            
            # Simple check: wait for profile icon or login form
            # Adjust selector based on actual site content. 
            # Assuming profile icon has some class or ID.
            # If we can't be sure, we just pause and ask user.
            
            # For now, we will perform a heuristic check. 
            # If user hasn't logged in before, they likely need to.
            
            # We'll just wait for the user to confirm in the UI (or we can automate the wait).
            # Better approach: Open the page, tell user "Please login in the browser window if not already",
            # then wait for a signal or poll for a specific element.
            
            self.log("Waiting for you to log in... (Close the browser window when done)")
            
            # Wait loop: Check if page/browser is closed every 1 second
            while not page.is_closed() and self.browser.is_connected():
                await asyncio.sleep(1)

            # NOTE: If user closed the page, we can't save state easily if context is gone?
            # Actually, if page is closed, context might still be open. 
            # But standard behavior: User closes window -> Page closes.
            # We need to save state JUST BEFORE close or implies user finished.
            
            # Ideally, user should click a button in our GUI "I finished Login"? 
            # Or we autosave periodically?
            
            # Let's save logic: We will save state every few seconds WHILE user is logging in, 
            # so that when they close, we have the latest state.
            
        except Exception as e:
            self.log(f"Login check failed (or window closed): {e}")
        finally:
            # Try to save one last time if context is still valid
            try:
                await context.storage_state(path=self.storage_state_path)
                self.log("Session saved to disk.")
            except:
                pass
            await context.close()

    async def perform_login_flow(self):
        """
        Runs the full login lifecycle in a single event loop.
        """
        await self.start_browser(headless=False)
        await self.ensure_login()
        await self.close()

    async def perform_full_job(self, tickers, models, cme_tickers, cme_models, download_folder, parallel):
        """
        Runs the full job lifecycle (Start -> Run -> Close) in a single loop.
        """
        try:
            await self.start_browser(headless=False)
            await self.run_scraping_job(tickers, models, cme_tickers, cme_models, download_folder, parallel)
        finally:
            await self.close()

    async def run_scraping_job(self, tickers: list, models: list, cme_tickers: list, cme_models: list, download_folder: str, parallel_mode: bool = False):
        """
        Main scrapping logic.
        """
        self.stop_requested = False
        if not os.path.exists(self.storage_state_path):
             self.log("No session file found. Please use 'Log in via Browser' first.")
             return

        self.success_count = 0
        self.failed_items = []

        self.log(f"Starting job. Std: {len(models)} models, CME: {len(cme_models)} models.")
        
        # Prepare TV Code aggregation bucket (Shared?)
        # Let's keep them separate or shared? User "除了 TV Code，其他 model 多一層 Ticker name 的資料夾"
        # User requested "CME Download folder 路徑多一層 CME"
        # "CME model select"
        # Since TV Code is aggregated, maybe create separate TV Code files for CME vs Standard? 
        # Or one big file? User didn't specify. I'll make separate lists to be safe or just pass "subfolder" context.
        
        tv_codes_std = []
        tv_codes_cme = []
        
        if not self.browser:
            await self.start_browser(headless=False)

        context = await self.browser.new_context(storage_state=self.storage_state_path, accept_downloads=True)
        
        tasks = []
        
        # 1. Standard Platform Tasks
        if tickers and models:
            for i, model in enumerate(models):
                if self.stop_requested:
                    # In sequential mode, this catches future models
                    for skipped_model in models[i:]:
                        for t in tickers:
                            self.failed_items.append(f"[{skipped_model}] {t} (Stopped)")
                    break
                    
                # Standard URL, No prefix
                coro = self.process_model_queue(context, model, tickers, download_folder, tv_codes_std, target_url=f"{BASE_URL}/platform", subfolder_prefix="")
                if parallel_mode:
                    tasks.append(coro)
                else:
                    await coro

        # 2. CME Platform Tasks
        if cme_tickers and cme_models:
            CME_URL = f"{BASE_URL}/platform/cme"
            for i, model in enumerate(cme_models):
                if self.stop_requested:
                    # In sequential mode, this catches future models
                    for skipped_model in cme_models[i:]:
                        for t in cme_tickers:
                            self.failed_items.append(f"[{skipped_model}] {t} (Stopped)")
                    break
                    
                # CME URL, "CME" prefix
                coro = self.process_model_queue(context, model, cme_tickers, download_folder, tv_codes_cme, target_url=CME_URL, subfolder_prefix="CME")
                if parallel_mode:
                    tasks.append(coro)
                else:
                    await coro

        if parallel_mode and tasks:
            await asyncio.gather(*tasks)
        
        # Save TV codes
        if tv_codes_std:
            self.save_tv_codes(tv_codes_std, download_folder, subfolder="")
        if tv_codes_cme:
            self.save_tv_codes(tv_codes_cme, download_folder, subfolder="CME")
            
        self.log_summary()

    def log_summary(self):
        total = self.success_count + len(self.failed_items)
        self.log("\n" + "="*30)
        self.log(f"JOB SUMMARY")
        self.log(f"Total Processed: {total}")
        self.log(f"Success: {self.success_count}")
        self.log(f"Failed: {len(self.failed_items)}")
        if self.failed_items:
            self.log("Failed Items:")
            for item in self.failed_items:
                self.log(f" - {item}")
        self.log("="*30 + "\n")
            
        # await context.close() # Done in caller wrapper

    async def process_model_queue(self, context, model, tickers, download_folder, tv_codes_list, target_url, subfolder_prefix=""):
        """
        Processes all tickers for a single model in one page.
        """
        page = await context.new_page()
        try:
            prefix_log = f"[CME-{model}]" if subfolder_prefix else f"[{model}]"
            self.log(f"{prefix_log} Page initialized.")
            await page.goto(target_url)
            await page.wait_for_load_state("networkidle")
            
            # Select Model
            await page.get_by_text("Select model", exact=False).first.click()
            await asyncio.sleep(0.5)
            await page.get_by_text(model, exact=True).first.click()
            self.log(f"{prefix_log} Model selected.")

            for i, ticker in enumerate(tickers):
                if self.stop_requested:
                    self.log(f"{prefix_log} Stopped. Skipping remaining tickers.")
                    for skipped_ticker in tickers[i:]:
                         self.failed_items.append(f"{prefix_log} {skipped_ticker} (Stopped)")
                    break
                
                await self.process_single_ticker(page, model, ticker, download_folder, tv_codes_list, subfolder_prefix)
                
        except Exception as e:
            self.log(f"{prefix_log} Error: {e}")
        finally:
            await page.close()

    async def process_single_ticker(self, page, model, ticker, download_folder, tv_codes_list, subfolder_prefix):
        max_retries = 10
        for attempt in range(max_retries):
            if self.stop_requested: 
                prefix_log = f"[CME-{model}]" if subfolder_prefix else f"[{model}]"
                self.failed_items.append(f"{prefix_log} {ticker} (Stopped)")
                return
            try:
                # 2. Input Ticker
                # Placeholder "Ticker"
                await page.get_by_placeholder("Ticker").fill(ticker)
                
                # 3. Enter
                await page.get_by_role("button", name="Enter").click()
                
                # 4. Wait for processing
                # Detection: "Download" button becomes enabled? Or data appears?
                # User said "wait for data load out".
                # We can wait for a spinner to disappear or "Download" to trigger.
                # Let's wait for the "Download" button to be clickable/enabled.
                
                # Also handle "System Busy" or failure texts here if they exist.
                
                download_btn = page.get_by_role("button", name="下載") # Chinese "Download"
                # Or English "Download" depending on lang. Screenshot shows "下載".
                
                # Wait for response
                # We'll wait up to 30s
                await asyncio.sleep(2) # Min wait
                
                # If model is TV Code, we scrape text
                if model == "TV Code":
                    # ... (Extraction logic remains same) ...
                    # Wait for results to appear
                    await page.wait_for_selector("text=Put Wall", state="visible", timeout=60000) 
                    
                    content = await page.evaluate("() => document.body.innerText")
                    # Naive extraction: find line with Ticker
                    found_code = False
                    for line in content.split('\n'):
                        # Line format usually: "SPX" .... "Put Wall" ...
                        # Check if matches current ticker to ensure we aren't reading stale data
                        if (f'"{ticker}"' in line or line.startswith(f'"{ticker}"')) and "Put Wall" in line:
                            tv_codes_list.append(line.strip('" '))
                            self.log(f"[{model}] {ticker} - Code extracted.")
                            self.success_count += 1
                            found_code = True
                            break
                    
                    if not found_code:
                        raise Exception(f"Validation failed: No data found for ticker {ticker} (Stale data from previous search?)")
                else:
                    # Standard Download
                    async with page.expect_download(timeout=60000) as download_info:
                        await download_btn.click()
                    
                    download = await download_info.value
                    
                    # Structure: 
                    # Standard: download_folder/Model/Ticker/Ticker_date.HTML
                    # CME: download_folder/CME/Model/Ticker/Ticker_date.HTML
                    
                    if subfolder_prefix:
                        # e.g. "CME"
                        model_dir = os.path.join(download_folder, subfolder_prefix, utils.clean_filename(model), utils.clean_filename(ticker))
                    else:
                        model_dir = os.path.join(download_folder, utils.clean_filename(model), utils.clean_filename(ticker))
                        
                    os.makedirs(model_dir, exist_ok=True)
                    
                    save_path = os.path.join(model_dir, f"{ticker}_{utils.get_timestamp_filename(prefix='', extension='.html')}")
                    await download.save_as(save_path)
                    self.log(f"[{model}] {ticker} - Downloaded.")
                    self.success_count += 1

                break # Success, break retry loop

            except Exception as e:
                self.log(f"[{model}] {ticker} - Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    self.log(f"[{model}] {ticker} - Skipped after retries.")
                    self.failed_items.append(f"[{model}] {ticker}")
                await asyncio.sleep(2)

    def save_tv_codes(self, codes, download_folder, subfolder=""):
        if not codes:
            return
        
        # Structure: 
        # Standard: download_folder/TV Code/TV_Codes_date.txt
        # CME: download_folder/CME/TV Code/TV_Codes_date.txt
        
        if subfolder:
            tv_dir = os.path.join(download_folder, subfolder, "TV Code")
        else:
            tv_dir = os.path.join(download_folder, "TV Code")
            
        os.makedirs(tv_dir, exist_ok=True)
        
        filename = utils.get_timestamp_filename(prefix="TV_Codes", extension=".txt")
        info_lines = [f"{code}" for code in codes]
        content = "\n".join(info_lines)
        
        path = os.path.join(tv_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.log(f"Saved aggregated TV codes to {path}")
