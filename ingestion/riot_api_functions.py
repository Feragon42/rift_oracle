from dotenv import load_dotenv
import os
import requests
import time
import pandas as pd

load_dotenv()
riot_api_key = os.getenv("RIOT_API_KEY")

valid_divisions = ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER']
valid_tiers = ['I', 'II', 'III', 'IV']
requests_limit_per_second = 20
requests_limit_per_2_minute = 100
requests_done = 0
window_start = time.time()
last_request_ts = 0.0

def safe_request(request_url: str):
    global requests_done, window_start, last_request_ts

    while True:
        now = time.time()

        # Reset 2-minute window when needed.
        if now - window_start >= 120:
            window_start = now
            requests_done = 0

        if requests_done >= requests_limit_per_2_minute:
            wait_time = max(0.0, 120 - (now - window_start))
            print(f"Rate limit reached. Waiting for {wait_time:.2f} seconds before making more requests")
            time.sleep(wait_time)
            continue

        min_interval = 1 / requests_limit_per_second
        elapsed_since_last = now - last_request_ts
        if elapsed_since_last < min_interval:
            time.sleep(min_interval - elapsed_since_last)

        response = requests.get(request_url, timeout=30)
        requests_done += 1
        last_request_ts = time.time()

        if response.status_code == 429:  # Too Many Requests
            retry_after = int(response.headers.get("Retry-After", 1))
            print(f"Rate limit exceeded. Retrying after {retry_after} seconds")
            time.sleep(retry_after)
            continue

        return response

def get_summoners_data_by_division(division: str , tier : str, region: str = 'na1', queue: str = 'RANKED_SOLO_5x5'):
    if not riot_api_key:
        raise ValueError("RIOT_API_KEY is not set in environment variables.")

    if division.upper() not in valid_divisions:
        raise ValueError(f"Invalid division: {division}. Valid divisions are: {valid_divisions}")
    if tier.upper() not in valid_tiers:
        raise ValueError(f"Invalid tier: {tier}. Valid tiers are: {valid_tiers}")
    
    if division.upper() in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
        api_to_use = f'/lol/league/v4/{division.lower()}leagues/by-queue/{queue}'
        api_url = f'https://{region}.api.riotgames.com{api_to_use}?api_key={riot_api_key}'
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
            api_url = f'https://{region}.api.riotgames.com{api_to_use}?page={page_num}&api_key={riot_api_key}'
            
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

def save_summoners_dataset(summoners_data, filename: str, file_directory: str = '../datasets/bronze/riot_api/'):
    os.makedirs(file_directory, exist_ok=True)
    df = pd.DataFrame(summoners_data)
    df.to_json(f'{file_directory}{filename}', orient='records', lines=True)

def get_summoners_data():
    processed_logs = []
    for division in valid_divisions:
        valid_tiers_for_division = valid_tiers if division not in ['MASTER', 'GRANDMASTER', 'CHALLENGER'] else ['I']
        for tier in valid_tiers_for_division:
            try:
                summoners_data, total_pages = get_summoners_data_by_division(division, tier)
                save_summoners_dataset(summoners_data, f'summoners_{division}_{tier}.json')
    
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
    
    pd.DataFrame(processed_logs).to_csv(f'../datasets/bronze/riot_api/{time.strftime("%Y-%m-%d", time.gmtime())}_summoners_data_processing_log.csv', index=False)
    return processed_logs