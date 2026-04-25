"""
GEX Scraper CLI - Headless 自動化模式
供 n8n 或排程任務定時呼叫，無需 GUI。

用法：
  python cli.py                          # 使用 settings.json 的設定，執行全部
  python cli.py --models "TV Code"       # 只跑 TV Code 模型
  python cli.py --groups "Index,科技股"  # 只跑指定分組
  python cli.py --headless               # 使用 headless 瀏覽器（無視窗，伺服器適用）
  python cli.py --dry-run                # 只印出設定，不實際執行
"""

import asyncio
import argparse
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 加入腳本所在目錄到 PATH
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from scraper import LietaScraper
from utils import load_tickers_with_groups

# ── 路徑設定 ────────────────────────────────────────────────────────────────

GDRIVE_BASE = (
    "/Users/jeff/Library/CloudStorage/"
    "GoogleDrive-cccnahaha@gmail.com/"
    "其他電腦/My Mac (1)/Desktop"
)

DEFAULT_SETTINGS = {
    "ticker_filepath": f"{GDRIVE_BASE}/GEX scratcher/ticker_list_index.txt",
    "cme_ticker_filepath": f"{GDRIVE_BASE}/GEX scratcher/ticker_list_index_CME.txt",
    "download_folder": f"{GDRIVE_BASE}/GEX scratcher",
    "selected_models": ["Gamma", "Term", "Smile", "TV Code"],
    "selected_cme_models": ["Gamma", "Smile", "Term", "TV Code"],
    "parallel": True,
    "browser": "brave",
}

SETTINGS_FILE = SCRIPT_DIR / "settings.json"
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging() -> logging.Logger:
    """設定日誌，同時輸出到 console 和檔案"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"cli_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return logging.getLogger("GEX_CLI")


def load_settings() -> dict:
    """讀取 settings.json，合併預設值"""
    settings = DEFAULT_SETTINGS.copy()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 更新路徑到當前機器
            for key in ["ticker_filepath", "cme_ticker_filepath", "download_folder"]:
                if key in saved:
                    path = saved[key]
                    # 如果是舊路徑格式（jefflin），替換為新路徑
                    if "/Users/jefflin/" in path:
                        path = path.replace(
                            "/Users/jefflin/Desktop",
                            f"{GDRIVE_BASE}"
                        )
                    saved[key] = path
            settings.update(saved)
        except Exception as e:
            print(f"⚠️  讀取 settings.json 失敗，使用預設值：{e}")
    return settings


def parse_args():
    parser = argparse.ArgumentParser(
        description="GEX Scraper CLI - 自動化抓取 GEX 數據"
    )
    parser.add_argument(
        "--models",
        type=str,
        default="",
        help='要執行的模型，逗號分隔，如 "TV Code,Gamma"（預設：settings.json 的設定）',
    )
    parser.add_argument(
        "--cme-models",
        type=str,
        default="",
        help='CME 模型，逗號分隔（預設：settings.json 的設定）',
    )
    parser.add_argument(
        "--groups",
        type=str,
        default="",
        help='只跑指定 ticker 分組，逗號分隔，如 "Index,科技股"（預設：全部）',
    )
    parser.add_argument(
        "--tv-code-only",
        action="store_true",
        help="只抓 TV Code 模型（快速模式，約 5 分鐘）",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用 headless 瀏覽器（無視窗，適合伺服器/排程）",
    )
    parser.add_argument(
        "--no-cme",
        action="store_true",
        help="跳過 CME 期貨",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=None,
        help="平行執行（加速但較佔資源）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只印出設定，不實際執行",
    )
    parser.add_argument(
        "--result-json",
        type=str,
        default="",
        help="執行完成後輸出結果 JSON 到指定路徑",
    )
    parser.add_argument(
        "--retry-failed-file",
        type=str,
        default="",
        help="讀取 failed tasks JSON，僅執行 retry",
    )
    return parser.parse_args()


def get_tickers_for_groups(ticker_filepath: str, groups: list[str]) -> list[str]:
    """從 ticker_list_index.txt 取得指定分組的 tickers"""
    all_groups = load_tickers_with_groups(ticker_filepath)
    if not groups:
        # 全部分組
        tickers = []
        for group_tickers in all_groups.values():
            tickers.extend(group_tickers)
        return list(dict.fromkeys(tickers))  # 去重，保持順序

    tickers = []
    for group in groups:
        group = group.strip()
        if group in all_groups:
            tickers.extend(all_groups[group])
        else:
            print(f"⚠️  找不到分組：{group}，可用：{list(all_groups.keys())}")
    return list(dict.fromkeys(tickers))


async def run_scraper(
    tickers: list[str],
    models: list[str],
    cme_tickers: list[str],
    cme_models: list[str],
    download_folder: str,
    parallel: bool,
    headless: bool,
    logger: logging.Logger,
):
    """執行 Scraper 的非同步函數"""

    def log_func(msg: str):
        logger.info(msg)

    scraper = LietaScraper(logger_func=log_func, browser_type="brave")

    # 啟動瀏覽器
    await scraper.start_browser(headless=headless)
    if headless:
        logger.info("✅ Headless 模式啟動")
    else:
        logger.info("✅ 瀏覽器已啟動（有視窗）")

    result = {
        "initial_failed_tasks": [],
        "retry_failed_tasks": [],
        "retried": False,
        "total_processed": 0,
        "success_count": 0,
        "failed_count": 0,
    }
    try:
        failed_tasks = await scraper.run_scraping_job(
            tickers=tickers,
            models=models,
            cme_tickers=cme_tickers,
            cme_models=cme_models,
            download_folder=download_folder,
            parallel_mode=parallel,
        )
        result["initial_failed_tasks"] = failed_tasks or []
        result["success_count"] = int(getattr(scraper, "success_count", 0))
        result["failed_count"] = len(result["initial_failed_tasks"])
        result["total_processed"] = result["success_count"] + result["failed_count"]
        # 依需求：一般 run 不自動觸發 retry；僅由 API /scraper-retry-failed 手動重試
        if failed_tasks:
            logger.warning(f"⚠️  本次有 {len(failed_tasks)} 個失敗（未自動 Retry）")

    finally:
        await scraper.close()
    return result


async def run_retry_only(
    failed_tasks: list[dict],
    download_folder: str,
    parallel: bool,
    headless: bool,
    logger: logging.Logger,
):
    """僅針對 failed tasks 執行 retry。"""
    def log_func(msg: str):
        logger.info(msg)

    scraper = LietaScraper(logger_func=log_func, browser_type="brave")
    await scraper.start_browser(headless=headless)
    try:
        remaining = await scraper.retry_scraping_job(
            failed_tasks=failed_tasks,
            download_folder=download_folder,
            parallel_mode=parallel,
        )
        success_count = int(getattr(scraper, "success_count", 0))
        failed_count = len(remaining or [])
        return {
            "initial_failed_tasks": failed_tasks,
            "retry_failed_tasks": remaining or [],
            "retried": True,
            "retry_only": True,
            "total_processed": success_count + failed_count,
            "success_count": success_count,
            "failed_count": failed_count,
        }
    finally:
        await scraper.close()


def main():
    args = parse_args()
    logger = setup_logging()
    settings = load_settings()

    logger.info("=" * 50)
    logger.info(f"🚀 GEX Scraper CLI 啟動 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # 決定模型
    if args.tv_code_only:
        models = ["TV Code"]
        cme_models = ["TV Code"]
    else:
        models = [m.strip() for m in args.models.split(",")] if args.models else settings["selected_models"]
        cme_models = [m.strip() for m in args.cme_models.split(",")] if args.cme_models else settings["selected_cme_models"]

    # 決定 tickers
    ticker_filepath = settings["ticker_filepath"]
    groups = [g.strip() for g in args.groups.split(",")] if args.groups else []
    tickers = get_tickers_for_groups(ticker_filepath, groups)

    # CME tickers
    if args.no_cme:
        cme_tickers = []
    else:
        cme_ticker_filepath = settings.get("cme_ticker_filepath", "")
        if os.path.exists(cme_ticker_filepath):
            cme_tickers = get_tickers_for_groups(cme_ticker_filepath, [])
        else:
            cme_tickers = []

    # 平行模式
    parallel = settings.get("parallel", True)
    if args.parallel is not None:
        parallel = args.parallel

    # headless 模式
    headless = args.headless

    download_folder = settings["download_folder"]

    # 印出設定摘要
    logger.info(f"📂 下載資料夾：{download_folder}")
    logger.info(f"📋 Standard Tickers：{len(tickers)} 個")
    logger.info(f"📋 Standard 模型：{models}")
    logger.info(f"📋 CME Tickers：{len(cme_tickers)} 個")
    logger.info(f"📋 CME 模型：{cme_models}")
    logger.info(f"⚙️  平行模式：{parallel}")
    logger.info(f"⚙️  Headless：{headless}")

    if args.dry_run:
        logger.info("ℹ️  Dry-run 模式，不實際執行")
        return

    if not os.path.exists(settings.get("download_folder", "")):
        logger.error(f"❌ 下載資料夾不存在：{download_folder}")
        sys.exit(1)

    state_file = SCRIPT_DIR / "state.json"
    if not state_file.exists():
        logger.error("❌ 找不到 state.json，請先用 GUI 執行 'Log in via Browser'")
        sys.exit(1)

    # 執行 Scraper
    start_time = datetime.now()
    if args.retry_failed_file:
        with open(args.retry_failed_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        failed_tasks = payload if isinstance(payload, list) else payload.get("failed_tasks", [])
        if not isinstance(failed_tasks, list):
            logger.error("❌ retry failed 檔案格式錯誤")
            sys.exit(1)
        run_result = asyncio.run(
            run_retry_only(
                failed_tasks=failed_tasks,
                download_folder=download_folder,
                parallel=parallel,
                headless=headless,
                logger=logger,
            )
        )
    else:
        run_result = asyncio.run(
            run_scraper(
                tickers=tickers,
                models=models,
                cme_tickers=cme_tickers,
                cme_models=cme_models,
                download_folder=download_folder,
                parallel=parallel,
                headless=headless,
                logger=logger,
            )
        )
    elapsed = (datetime.now() - start_time).total_seconds()
    final_failed = run_result.get("retry_failed_tasks", []) or run_result.get("initial_failed_tasks", [])
    summary = {
        "success": len(final_failed) == 0,
        "elapsed_seconds": round(elapsed, 2),
        "initial_failed_count": len(run_result.get("initial_failed_tasks", [])),
        "retry_failed_count": len(run_result.get("retry_failed_tasks", [])),
        "failed_tasks": final_failed,
        "retried": bool(run_result.get("retried")),
        "retry_only": bool(run_result.get("retry_only")),
        "finished_at": datetime.now().isoformat(),
    }
    if args.result_json:
        with open(args.result_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 完成！耗時 {elapsed:.0f} 秒")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
