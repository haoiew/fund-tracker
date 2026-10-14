"""Configure writable Android storage before importing the shared application."""
import os
import time


def start(files_dir: str) -> str:
    os.environ["FUND_TRACKER_DATA_DIR"] = files_dir
    # Fund dates and the daily NAV job use the Shanghai market clock. Avoid tzlocal's
    # Android getprop subprocess, which resets ART-owned signal handlers after fork.
    os.environ["TZ"] = "Asia/Shanghai"
    if hasattr(time, "tzset"):
        time.tzset()
    from app.embedded import start_backend
    return start_backend()
