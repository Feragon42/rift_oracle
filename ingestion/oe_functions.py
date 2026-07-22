import os
import time
from datetime import datetime, timedelta
import shutil
import re
import gdown
from pathlib import Path
from metadata import metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze' / 'oe'

def download_oe_data(year: int | None = None) -> str: #Execute daily until it successfully downloads the file
    if year is None:
        year = int(time.strftime("%Y"))
    
    last_request_time, downloaded = metadata.check_last_oracle_elixir_requested(year)

    if downloaded and last_request_time > (datetime.now() - timedelta(weeks=1)).isoformat():
        return True

    folder_url = "https://drive.google.com/drive/u/0/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH"
    file_name = f"{year}_LoL_esports_match_data_from_OraclesElixir.csv"
    final_path = DATASETS_DIR / file_name

    os.makedirs(DATASETS_DIR, exist_ok=True)

    # A Drive folder URL is not a file path. Download folder contents, then move only the target file to the final destination.
    temp_dir = os.path.join(DATASETS_DIR, "_tmp_gdrive_download")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        gdown.download_folder(url=folder_url, output=temp_dir)
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Error downloading from Google Drive: {exc}")
        metadata.log_oracle_elixir_request(year=year, downloaded=False, error_message=str(exc))
        return False

    downloaded_file_path = None
    for root, _, files in os.walk(temp_dir):
        if file_name in files:
            downloaded_file_path = os.path.join(root, file_name)
            break

    if downloaded_file_path is None:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise FileNotFoundError(f"Could not find '{file_name}' inside Drive folder download.")

    shutil.move(downloaded_file_path, str(final_path))
    shutil.rmtree(temp_dir, ignore_errors=True)
    metadata.log_oracle_elixir_request(year=year, downloaded=True, error_message=None)

    return True