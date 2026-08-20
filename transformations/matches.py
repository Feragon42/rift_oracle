import pandas as pd
import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'silver'
BRONZE_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze'

def upload_oe_matches(rewrite=False) -> bool:
    match_summary_columns = ['date','side','position','playername','champion','gamelength','result','kills','deaths','assists',
                            'teamkills','teamdeaths','doublekills','triplekills','quadrakills','pentakills','damagetochampions',
                            'dpm','damageshare','damagetakenperminute','damagemitigatedperminute','damagetotowers','total cs',
                            'killsat10','assistsat10','deathsat10','csat10','opp_killsat10','opp_assistsat10','opp_deathsat10','opp_csat10',
                            'killsat15','assistsat15','deathsat15','csat15','opp_killsat15','opp_assistsat15','opp_deathsat15','opp_csat15',
                            'killsat20','assistsat20','deathsat20','csat20','opp_killsat20','opp_assistsat20','opp_deathsat20','opp_csat20',
                            'killsat25','assistsat25','deathsat25','csat25','opp_killsat25','opp_assistsat25','opp_deathsat25','opp_csat25']
    ban_list_columns = ['date', 'gameid', 'side', 'ban1', 'ban2', 'ban3', 'ban4', 'ban5']
    matches_summary_dir = SILVER_DATASETS_DIR / 'pro_matches_summary.parquet'
    ban_list_dir = SILVER_DATASETS_DIR / 'pro_matches_ban_list.parquet'

    ##Get first and last patch dates from the patches dimension
    first_available_patch_date, last_available_patch_date = get_patch_dates()

    ##Get last match date from the procceded matches
    last_processed_match_date = get_last_match_date() if rewrite == False else None

    ##Get list of years to process. The files are named by year.
    years_list = list(range(first_available_patch_date.year, datetime.now().year + 1))

    ##Get matches and ban list parquet files or create empty DataFrames if I will rewrite the data
    if os.path.exists(matches_summary_dir) and rewrite == False:
        matches_summary_df = pd.read_parquet(matches_summary_dir, engine='pyarrow')
    else:
        matches_summary_df = pd.DataFrame(columns=match_summary_columns)

    if os.path.exists(ban_list_dir) and rewrite == False:
        ban_list_df = pd.read_parquet(ban_list_dir, engine='pyarrow')
    else:
        ban_list_df = pd.DataFrame(columns=ban_list_columns)

    ##Iterate over the years and process the matches and ban list data
    for year in years_list:
        source_file_dir = BRONZE_DATASETS_DIR / 'oe' / f'{year}_LoL_esports_match_data_from_OraclesElixir.csv'
        if not os.path.exists(source_file_dir):
            raise ValueError(f"The source file for year {year} does not exist. Please check the data source.")
        else:
            oe_df = pd.read_csv(source_file_dir)
            oe_df['date'] = pd.to_datetime(oe_df['date'], errors='coerce')

            #Filter the DataFrame to only include not processed matches
            if last_processed_match_date is not None:
                oe_df = oe_df[(oe_df['date'] >= last_processed_match_date)]

            #Filter and group data as needed in the resulting parquets
            matches_summary_df = pd.concat([matches_summary_df, oe_df.loc[:, match_summary_columns].rename(columns={'total cs': 'total_cs'}).copy().dropna(subset=['date','champion'])], ignore_index=True)
            ban_list_df = pd.concat([ban_list_df, oe_df.loc[:, ban_list_columns].copy().dropna(subset=['date','gameid','ban1']).drop_duplicates(subset=['date','gameid','side'], keep='first')], ignore_index=True)

            #Create parquets
            try:
                matches_summary_df.to_parquet(matches_summary_dir, engine='pyarrow', index=False)
                ban_list_df.to_parquet(ban_list_dir, engine='pyarrow', index=False)
            except Exception as e:
                raise ValueError(f"Failed to write the matches summary or ban list DataFrame to Parquet format. Please check the data and try again. Error: {e}")

    return True


def get_patch_dates(patch_number: int | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
    if not os.path.exists(SILVER_DATASETS_DIR/'patches_dimension.parquet'):
        raise ValueError("The patches_dimension.parquet file does not exist. Please check the data source.")
    else:
        patches = pd.read_parquet(SILVER_DATASETS_DIR/'patches_dimension.parquet', engine='pyarrow')
        if patches.empty:
            raise ValueError("The patches_dimension.parquet file is empty. Please check the data source.")
        else:
            if patch_number is not None:
                patch_row = patches[patches['patch_number'] == patch_number]
                if patch_row.empty:
                    raise ValueError(f"The patch number {patch_number} does not exist in the patches_dimension.parquet file.")
                else:
                    first_patch_date = patch_row['patch_start_date'].values[0]
                    last_patch_date = patch_row['patch_end_date'].values[0]                
            else:
                first_patch_date = patches['patch_start_date'].min()
                last_patch_date = patches['patch_end_date'].max()

    return first_patch_date, last_patch_date

def get_last_match_date() -> pd.Timestamp | None:
    if not os.path.exists(SILVER_DATASETS_DIR/'pro_matches_summary.parquet'):
        return None
    else:
        matches = pd.read_parquet(SILVER_DATASETS_DIR/'pro_matches_summary.parquet', engine='pyarrow')
        if matches.empty:
            return None
        else:
            last_match_date = matches['date'].max()
            return last_match_date