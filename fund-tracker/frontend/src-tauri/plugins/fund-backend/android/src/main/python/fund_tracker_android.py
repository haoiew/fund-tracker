"""Configure writable Android storage before importing the shared application."""
import os


def start(files_dir: str) -> str:
    os.environ["FUND_TRACKER_DATA_DIR"] = files_dir
    from app.embedded import start_backend
    return start_backend()
