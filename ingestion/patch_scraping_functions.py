import re
import time
import pandas as pd
import requests
from html import unescape
from urllib.parse import urlparse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from metadata import metadata
import os
from dotenv import load_dotenv
from pathlib import Path
from google import genai
import base64
import json

load_dotenv()  # Load environment variables from .env file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze' / 'patches'
IMAGES_DIR = PROJECT_ROOT / 'datasets' / 'bronze' / 'patches' / 'patch_highlight_images'

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def _parse_patch_number(title_text: str) -> str:
    match = re.search(r"Patch\s+([0-9]+(?:\.[0-9]+)?)", title_text, re.IGNORECASE)
    return match.group(1) if match else title_text.strip()

def _patch_version_key(version: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?", str(version).strip())
    if not match:
        return (-1, -1)

    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    return (major, minor)


def scrape_patch_notes():
    url = "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/"

    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service("/usr/bin/chromedriver"),
        options=chrome_options,
    )
    wait = WebDriverWait(driver, 10)
    html = ""
    patch_rows = []

    try:
        driver.get(url)

        while True:
            try:
                show_more_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'cta')][.//span[normalize-space()='SHOW MORE'] or normalize-space()='SHOW MORE']"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_more_button)
                time.sleep(0.5)
                previous_count = len(driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-title']"))
                show_more_button.click()
                wait.until(lambda current_driver: len(current_driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-title']")) > previous_count)
            except (TimeoutException, NoSuchElementException):
                break

        html = driver.page_source

        for title_element in driver.find_elements(By.CSS_SELECTOR, "[data-testid='card-title']"):
            card_link = title_element.find_element(By.XPATH, "./ancestor::a[@href][1]")
            date_elements = card_link.find_elements(By.CSS_SELECTOR, "[data-testid='card-date']")
            title_text = title_element.text.strip()
            patch_rows.append(
                {
                    "patch_number": _parse_patch_number(title_text),
                    "patch_date": date_elements[0].text.strip() if date_elements else None,
                    "patch_url": card_link.get_attribute("href"),
                    "patch_title": title_text,
                }
            )
    finally:
        driver.quit()

    patches_df = (
        pd.DataFrame(patch_rows)
        .drop_duplicates(subset=["patch_url"])
        .reset_index(drop=True)
    )

    return patches_df

def _normalize_url(url: str) -> str:
    cleaned = url.strip()
    if cleaned.startswith("//"):
        return f"https:{cleaned}"
    return cleaned

def _guess_extension(image_url: str | None, content_type: str | None) -> str:
    if content_type:
        content_type = content_type.lower()
        if "png" in content_type:
            return "png"
        if "jpeg" in content_type or "jpg" in content_type:
            return "jpg"

    if image_url:
        path = urlparse(image_url).path.lower()
        if path.endswith(".png"):
            return "png"
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            return "jpg"

    return "jpg"


def _extract_highlight_urls_from_skins_anchor(page_html: str) -> list[str]:
    skins_anchor_pattern = re.compile(
        r"<a[^>]*class=['\"][^'\"]*skins[^'\"]*cboxElement[^'\"]*['\"][^>]*href=['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )
    normalized = unescape(page_html).replace("\\/", "/")
    matches = skins_anchor_pattern.findall(normalized)

    unique_urls = []
    seen = set()
    for url in matches:
        clean = _normalize_url(url)
        if clean not in seen:
            seen.add(clean)
            unique_urls.append(clean)

    return unique_urls


def _extract_cms_candidate_image_urls(page_html: str) -> list[str]:
    normalized = unescape(page_html).replace("\\/", "/")
    image_url_pattern = re.compile(r"https://cmsassets\.rgpub\.io/sanity/images/[^\s\"'<>\)]+", re.IGNORECASE)
    found = image_url_pattern.findall(normalized)

    unique_urls = []
    seen = set()
    for url in found:
        clean = _normalize_url(url.split("\"")[0].split("'")[0].rstrip(",)"))
        if clean not in seen:
            seen.add(clean)
            unique_urls.append(clean)

    return unique_urls

def save_image(content: bytes, content_type: str, output_dir: Path, filename: str) -> bool:
    try:
        if content is None:
            print(f"No image content")
            return False

        output_path = output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)

        print(f"Downloaded image")
        return True
    except requests.RequestException as exc:
        print(f"Failed to download")
        return False

def download_patch_highlight_image(patch_url: str, patch_version: str, timeout: int = 20) -> str:
    output_dir = IMAGES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    page_response = requests.get(patch_url, timeout=timeout)
    page_response.raise_for_status()

    # First try explicit highlight links from anchor tags.
    candidates = _extract_highlight_urls_from_skins_anchor(page_response.text)

    # Fallback: scan page for CMS image URLs.
    if not candidates:
        candidates = _extract_cms_candidate_image_urls(page_response.text)

    for candidate_url in candidates:
        try:
            image_response = requests.get(candidate_url, timeout=timeout)
            image_response.raise_for_status()
            content_type = image_response.headers.get("Content-Type", "")
            if content_type.startswith("image/"):
                extension = _guess_extension(candidate_url, content_type)
                filename = f"{patch_version}_patch_highlights.{extension}"
                r = save_image(image_response.content, content_type, output_dir, filename)
                if r:
                    return filename
        except requests.RequestException:
            continue

    return None

def get_gemini_patch_image_analysis(filename: str, patch_version: str) -> list[dict]:
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in your environment before running this cell.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    image_bytes = (IMAGES_DIR / filename).read_bytes()
    if not image_bytes:
        print(f"Image file {filename} is empty or not found.")
        return {}

    interaction = client.interactions.create(
        model="gemini-3.5-flash",
        input=[
            {
                "type": "text",
                "text": (
                    "Analyze this League of Legends patch highlight image. "
                    "Return ONLY valid JSON in this exact format: "
                    "{\"changes\": [{\"champion\": \"...\", \"change_type\": \"Buff|Nerf\", \"patch_number\": \"...\"}]} "
                    f"Use patch_number = '{patch_version}'. "
                    "If no champion buffs/nerfs are visible, return {\"changes\": []}."
                ),
            },
            {
                "type": "image",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": "image/png" if filename.lower().endswith(".png") else "image/jpeg",
            },
        ],
    )

    raw_text = interaction.output_text.strip()

    # Handle occasional fenced JSON responses.
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    payload = json.loads(raw_text)
    changes = payload.get("changes", [])

    

    return changes

def save_patch_changes_to_csv(changes: list[dict], patch_version: str) -> bool:
    if not changes:
        raise ValueError("No changes to save. The 'changes' list is empty.")
        return False

    output_file = DATASETS_DIR / f"patch_highlights_champion_changes_{patch_version}.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    df_records = []

    for change in changes:
        champion = str(change.get("champion", "")).strip()
        change_type = str(change.get("change_type", "")).strip().title()
        patch_num = str(change.get("patch_number", patch_version)).strip() or patch_version

        if champion and change_type in {"Buff", "Nerf"}:
            df_records.append(
                {
                    "Champion": champion,
                    "Change Type": change_type,
                    "Patch Number": patch_num
                }
            )

    df = pd.DataFrame(df_records)
    df.to_csv(output_file, index=False)

    return True

def get_new_patch_notes():
    try:
        patches_df = scrape_patch_notes()
    except Exception as e:
        print(f"Error scraping patch notes: {e}")
        return 0
    
    last_patch_version = _patch_version_key(metadata.get_last_patch_notes_requested())
    scraped_patch_file = DATASETS_DIR / "scraped_patch_notes.csv"

    if patches_df is None or patches_df.empty:
        return 0

    new_rows = []
    for _, row in patches_df.iterrows():
        patch_version = str(row["patch_number"]).strip()
        if _patch_version_key(patch_version) > last_patch_version and _patch_version_key(patch_version) != 2025: ##To ignore the format problem of Riot
            new_rows.append(row)

    if not new_rows:
        return 0

    new_patches_df = pd.DataFrame(new_rows)

    scraped_patch_file.parent.mkdir(parents=True, exist_ok=True)
    if scraped_patch_file.exists():
        existing_df = pd.read_csv(scraped_patch_file)
        combined_df = pd.concat([existing_df, new_patches_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["patch_url"], keep="last")
    else:
        combined_df = new_patches_df

    combined_df.to_csv(scraped_patch_file, index=False)

    for patch_version in sorted(new_patches_df["patch_number"].astype(str).unique(), key=_patch_version_key):
        print(f"Processing patch version: {patch_version}")
        filename = download_patch_highlight_image(patch_url=new_patches_df.loc[new_patches_df["patch_number"] == patch_version, "patch_url"].values[0], patch_version=patch_version)
        if filename:
            print(f"Downloaded image for patch {patch_version}: {filename}")
            patch_changes = get_gemini_patch_image_analysis(filename=filename, patch_version=patch_version)
            if patch_changes:
                print(f"Extracted changes for patch {patch_version}: {patch_changes}")
                r = save_patch_changes_to_csv(patch_changes, patch_version)
                if r:
                    print(f"Saved changes to CSV for patch {patch_version}")
                    metadata.log_patch_notes_request(patch_version)
                    print(f"Logged patch notes request for patch {patch_version}")
                else:
                    print(f"Failed to save changes to CSV for patch {patch_version}")
                    return False
            else:
                print(f"No changes extracted for patch {patch_version}")
                return False
        else:
            print(f"Failed to download image for patch {patch_version}")
            return False

    return True