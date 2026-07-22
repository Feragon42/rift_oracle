from dotenv import load_dotenv
from pathlib import Path
from collections import deque
import os
import requests
import time
import pandas as pd
import json
from metadata import metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze' / 'riot_api'

load_dotenv()
riot_api_key = os.getenv("RIOT_API_KEY")

#valid_divisions = ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER']
valid_divisions = ['DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER']
valid_tiers = ['I', 'II', 'III', 'IV']
requests_limit_per_second = 20
requests_limit_per_2_minute = 100
requests_last_second = deque()
requests_last_2_minute = deque()

def safe_request(request_url: str):
    global requests_last_second, requests_last_2_minute

    while True:
        now = time.monotonic()

        while requests_last_second and (now - requests_last_second[0]) >= 1.0:
            requests_last_second.popleft()
        while requests_last_2_minute and (now - requests_last_2_minute[0]) >= 120.0:
            requests_last_2_minute.popleft()

        wait_for_second = 0.0
        wait_for_2_minute = 0.0
        if len(requests_last_second) >= requests_limit_per_second:
            wait_for_second = max(0.0, 1.0 - (now - requests_last_second[0]))
        if len(requests_last_2_minute) >= requests_limit_per_2_minute:
            wait_for_2_minute = max(0.0, 120.0 - (now - requests_last_2_minute[0]))

        wait_time = max(wait_for_second, wait_for_2_minute)
        if wait_time > 0:
            if wait_for_2_minute >= wait_for_second and wait_for_2_minute > 0:
                print(f"Rate limit reached (100/120s). Waiting for {wait_time:.2f} seconds before making more requests")
            else:
                print(f"Rate limit reached (20/s). Waiting for {wait_time:.2f} seconds before making more requests")
            time.sleep(wait_time + 0.01)
            continue

        response = requests.get(request_url, timeout=30)
        request_ts = time.monotonic()
        requests_last_second.append(request_ts)
        requests_last_2_minute.append(request_ts)

        if response.status_code == 429:  # Too Many Requests
            retry_after = int(response.headers.get("Retry-After", 1))
            print(f"Rate limit exceeded. Retrying after {retry_after} seconds")
            time.sleep(retry_after)
            continue

        return response

def get_summoners_data_by_division(
        division: str , 
        tier : str, 
        news_only: bool = False, 
        region: str = 'na1', 
        queue: str = 'RANKED_SOLO_5x5'
):
    if not riot_api_key:
        raise ValueError("RIOT_API_KEY is not set in environment variables.")

    if division.upper() not in valid_divisions:
        raise ValueError(f"Invalid division: {division}. Valid divisions are: {valid_divisions}")
    if tier.upper() not in valid_tiers:
        raise ValueError(f"Invalid tier: {tier}. Valid tiers are: {valid_tiers}")
    
    news_param = '&freshBlood=True' if news_only else ''
    
    if division.upper() in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
        api_to_use = f'/lol/league/v4/{division.lower()}leagues/by-queue/{queue}'
        api_url = f'https://{region}.api.riotgames.com{api_to_use}?api_key={riot_api_key}{news_param}'
        response = safe_request(api_url)

        if response.status_code == 200:
            summoners_data = response.json().get('entries', [])
            return summoners_data, 1  # These divisions have only one page of data
        else:
            response.raise_for_status()
        
    else:
        api_to_use = f'/lol/league/v4/entries/{queue}/{division.upper()}/{tier.upper()}'
    
        page_num = 1
        summoners_data = []
        while True:
            api_url = f'https://{region}.api.riotgames.com{api_to_use}?page={page_num}&api_key={riot_api_key}{news_param}'
            
            response = safe_request(api_url)
            
            if response.status_code == 200:
                summoners_in_page = response.json()
                if not summoners_in_page:
                    break

                summoners_data.extend(summoners_in_page)
                page_num += 1
            else:
                response.raise_for_status()
        return summoners_data, page_num - 1

def save_summoners_dataset(summoners_data, filename: str):
    os.makedirs(DATASETS_DIR, exist_ok=True)
    df = pd.DataFrame(summoners_data)
    df.to_json(f'{DATASETS_DIR}/{filename}', orient='records', lines=True)

def get_summoners_data(news_only: bool = False): ##TODO Check Metadata for the last time a division was processed, to download freshBlood every month
    processed_logs = []
    for division in valid_divisions:
        valid_tiers_for_division = valid_tiers if division not in ['MASTER', 'GRANDMASTER', 'CHALLENGER'] else ['I']
        for tier in valid_tiers_for_division:
            try:
                summoners_data, total_pages = get_summoners_data_by_division(division, tier, news_only=news_only)
                save_summoners_dataset(summoners_data, f'{time.strftime("%Y-%m-%d", time.gmtime())}_summoners_{division}_{tier}.json')
    
                processed_logs.append({
                    'processed_time': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    'division': division,
                    'tier': tier,
                    'total_pages': total_pages,
                    'total_summoners': len(summoners_data[0]),
                    'status' : 'done'
                })
                
            except Exception as e:
                processed_logs.append({
                    'processed_time': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    'division': division,
                    'tier': tier,
                    'status': 'error',
                    'error_message': str(e)
                })
                continue
    
    pd.DataFrame(processed_logs).to_csv(f'{DATASETS_DIR}/{time.strftime("%Y-%m-%d", time.gmtime())}_summoners_data_processing_log.csv', index=False)
    return processed_logs

def create_summoners_puuid_list(division: str | None = None, tier: str | None = None, date: str | None = None): ##TODO Look for the date in the metadata of the last time a division was requested
    if not date:
        date = max([f.stem.split('_')[0] for f in Path(DATASETS_DIR).glob(f'*_summoners_*.json')])
        if not date:
            raise ValueError("No summoner data files found to determine the latest date.")
    
    puuid_list = []
    filelist = list(Path(DATASETS_DIR).glob(f'{date}_summoners_{division if division else "*"}_{tier if tier else "*"}.json'))
    for filename in filelist:
        if not Path(filename).exists():
            continue
        with open(Path(filename), 'r', encoding='utf-8') as f:
            for line in f:
                summoner = json.loads(line)
                puuid_list.append(summoner['puuid'])

    puuid_list = list(set(puuid_list))  # Remove duplicates
    return puuid_list, date


def get_match_id_list(division: str | None = None, tier: str | None = None, queue: str = 'ranked'):
    summoners_puuid_list, date_of_list = create_summoners_puuid_list(division=division, tier=tier)
    os.makedirs(DATASETS_DIR, exist_ok=True)
    result_filename = Path(DATASETS_DIR) / f'{date_of_list}_match_id_list_{division if division else "all"}_{tier if tier else "all"}.json'
    
    for summoner in summoners_puuid_list:
        try:
            last_requested_time = metadata.get_summoner_last_request_time(summoner)
            if last_requested_time:
                min_date = pd.Timestamp(last_requested_time)
            else:
                min_date = pd.Timestamp('2021-06-16')  # Default start date if no logs exist

            match_id_list = []
            now_date = pd.Timestamp.now().floor('D')
            while min_date < now_date:
                max_date = min_date + pd.Timedelta(days=10)
                if max_date > now_date:
                    max_date = now_date
                
                min_date_epoch = int(min_date.timestamp())
                max_date_epoch = int(max_date.timestamp())
                url = f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner}/ids?startTime={min_date_epoch}&endTime={max_date_epoch}&type={queue}&start=0&count=100&api_key={riot_api_key}'
                response = safe_request(url)
                if response.status_code != 200:
                    response.raise_for_status()

                retrieved_match_ids = response.json()
                match_id_list.extend(retrieved_match_ids)
                min_date = max_date

            unique_match_ids = list(dict.fromkeys(match_id_list))
            with open(result_filename, 'a', encoding='utf-8') as f:
                for match_id in unique_match_ids:
                    f.write(json.dumps({'summoner_puuid': summoner, 'match_id': match_id}) + '\n')

            # Persist the actual last successful fetch time, not the date of the summoner snapshot.
            metadata.update_summoner_request_time(summoner, now_date.isoformat())
        except Exception as e:
            continue
            
    return True

def get_match_info(match_id: str):
    last_requested_time = metadata.check_if_match_id_was_requested(match_id)
    if last_requested_time:
        return None  # Match info already requested, skip fetching

    url = f'https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}'
    response = safe_request(url)
    if response.status_code != 200:
        response.raise_for_status()

    match_info = response.json()
    metadata.update_match_id_request_time(match_id)
    return match_info

def process_match_list():
    match_id_list = []
    for file in Path(DATASETS_DIR).glob('*_match_id_list_*.json'):
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                match_entry = json.loads(line)
                match_id_list.append(match_entry['match_id'])
    
    match_info_results = open(Path(DATASETS_DIR) / f'{time.strftime("%Y-%m-%d", time.gmtime())}_match_info_results.json', 'a', encoding='utf-8')
    for match_id in match_id_list:
        match_info = get_match_info(match_id)
        if match_info:
            match_info_results.write(json.dumps(match_info) + '\n')
    match_info_results.close()
    return True