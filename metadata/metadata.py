import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = PROJECT_ROOT / 'metadata'


conn = sqlite3.connect(METADATA_DIR / 'pipelines.db')
cursor = conn.cursor()

def create_summoners_handling_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summoners_handling (
            summoner_puuid TEXT PRIMARY KEY,
            last_request_time TEXT,
            amount_of_requests INTEGER
        )
    ''')
    conn.commit()

def get_summoner_last_request_time(puuid):
    cursor.execute('SELECT last_request_time FROM summoners_handling WHERE summoner_puuid = ?', (puuid,))
    result = cursor.fetchone()
    return result[0] if result else None

def update_summoner_request_time(puuid, request_time):
    cursor.execute('''
        INSERT INTO summoners_handling (summoner_puuid, last_request_time, amount_of_requests)
        VALUES (?, ?, 1)
        ON CONFLICT(summoner_puuid) DO UPDATE SET
            last_request_time = excluded.last_request_time,
            amount_of_requests = amount_of_requests + 1
    ''', (puuid, request_time))
    conn.commit()

def create_match_id_handling_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_id_handling (
            match_id TEXT PRIMARY KEY,
            last_request_time TEXT
        )
    ''')
    conn.commit()

def check_if_match_id_was_requested(match_id):
    cursor.execute('SELECT last_request_time FROM match_id_handling WHERE match_id = ?', (match_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def update_match_id_request_time(match_id): 
    request_time = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO match_id_handling (match_id, last_request_time)
        VALUES (?, ?)
        ON CONFLICT(match_id) DO UPDATE SET
            last_request_time = excluded.last_request_time
    ''', (match_id, request_time))
    conn.commit()