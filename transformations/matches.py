import pandas as pd
import os
from datetime import datetime
from metadata import metadata
from transformations.patches import get_patch_dates
from transformations.utils import BRONZE_DATASETS_DIR, PRO_MATCHES_SUMMARY_FILE, SOLOQ_MATCHES_SUMMARY_FILE, PRO_MATCHES_BAN_LIST_FILE, SOLOQ_MATCHES_BAN_LIST_FILE, CHAMPIONS_DIMENSION_FILE

def upload_oe_matches(rewrite=False) -> bool:
    ##Get first and last patch dates from the patches dimension
    first_available_patch_date, last_available_patch_date = get_patch_dates()

    ##Get last match date from the procceded matches
    last_processed_match_date = pd.Timestamp(metadata.get_last_match_date("pro")) if rewrite == False else None

    ##Get list of years to process. The files are named by year.
    years_list = list(range(first_available_patch_date.year, datetime.now().year + 1))

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

            #Execute the processing functions for matches summary and ban list
            matches_summary_df = process_oe_match_summary(oe_df,rewrite)
            ban_list_df = process_oe_ban_list(oe_df,rewrite)

            if matches_summary_df.empty or ban_list_df.empty:
                raise ValueError(f"No new matches or ban list data to process for year {year}. Please check the data source.")

            #Create parquets
            try:
                matches_summary_df.to_parquet(PRO_MATCHES_SUMMARY_FILE, engine='pyarrow', index=False)
                ban_list_df.to_parquet(PRO_MATCHES_BAN_LIST_FILE, engine='pyarrow', index=False)
            except Exception as e:
                raise ValueError(f"Failed to write the matches summary or ban list DataFrame to Parquet format. Please check the data and try again. Error: {e}")

    #Update last match date in the database
    r = metadata.update_last_match_date("pro", matches_summary_df['date'].max())
    if not r:
        raise ValueError("Failed to update the last match date in the metadata database.")

    return True

def process_oe_ban_list(ban_list_df: pd.DataFrame, rewrite=False) -> pd.DataFrame:
    #ban_list_columns = ['date', 'patch', 'gameid', 'side', 'ban1', 'ban2', 'ban3', 'ban4', 'ban5']
    ban_list_columns = ['date', 'patch', 'gameid', 'side', 'ban']

    ##Get ban list parquet files or create empty DataFrames if I will rewrite the data
    if os.path.exists(PRO_MATCHES_BAN_LIST_FILE) and rewrite == False:
        ban_list_df = pd.read_parquet(PRO_MATCHES_BAN_LIST_FILE, engine='pyarrow')
    else:
        ban_list_df = pd.DataFrame(columns=ban_list_columns)

    #ban_list_df = pd.concat([ban_list_df, oe_df.loc[:, ban_list_columns].copy().dropna(subset=['date','gameid','ban']).drop_duplicates(subset=['date','gameid','side'], keep='first')], ignore_index=True)
    ban_list_df = pd.concat(
        [
            ban_list_df,
            ban_list_df.melt(
                id_vars=['date', 'patch', 'gameid', 'side'],
                value_vars=[f'ban{i+1}' for i in range(0,5)],
                var_name='ban_number',
                value_name='ban'
            )
            .drop(columns=['ban_number'])
            .dropna(subset=['date', 'gameid', 'ban'])
            .drop_duplicates(subset=['date','gameid','side','ban'], keep='first')
        ],
        ignore_index=True
    )
    return ban_list_df

def process_oe_match_summary(matches_summary_df: pd.DataFrame, rewrite=False) -> pd.DataFrame:
    match_summary_columns = ['date','patch','side','position','playername','champion','gamelength','result','kills','deaths','assists',
                            'teamkills','teamdeaths','doublekills','triplekills','quadrakills','pentakills','damagetochampions',
                            'dpm','damageshare','damagetakenperminute','damagemitigatedperminute','damagetotowers','total cs',
                            'killsat10','assistsat10','deathsat10','csat10','opp_killsat10','opp_assistsat10','opp_deathsat10','opp_csat10',
                            'killsat15','assistsat15','deathsat15','csat15','opp_killsat15','opp_assistsat15','opp_deathsat15','opp_csat15',
                            'killsat20','assistsat20','deathsat20','csat20','opp_killsat20','opp_assistsat20','opp_deathsat20','opp_csat20',
                            'killsat25','assistsat25','deathsat25','csat25','opp_killsat25','opp_assistsat25','opp_deathsat25','opp_csat25']

    ##Get matches parquet files or create empty DataFrames if I will rewrite the data
    if os.path.exists(PRO_MATCHES_SUMMARY_FILE) and rewrite == False:
        matches_summary_df = pd.read_parquet(PRO_MATCHES_SUMMARY_FILE, engine='pyarrow')
    else:
        matches_summary_df = pd.DataFrame(columns=match_summary_columns)

    matches_summary_df = pd.concat([matches_summary_df, 
                                    matches_summary_df.loc[:, match_summary_columns]
                                    .rename(columns={'total cs': 'total_cs'}).copy()
                                    .dropna(subset=['date','champion'])], 
                                    ignore_index=True)
    return matches_summary_df

def upload_soloq_matches(rewrite=False) -> bool:
    ##Get first and last patch dates from the patches dimension
    first_available_patch_date, last_available_patch_date = get_patch_dates()

    ##Get last match date from the procceded matches
    last_processed_match_date = pd.Timestamp(metadata.get_last_match_date("soloq")) if rewrite == False else None

    ##Get list of files to process. The files are named by the date when they were created.
    files_list = sorted([f for f in os.listdir(BRONZE_DATASETS_DIR / 'riot_api') 
                         if f.endswith('_match_info_results.json')
                         and f.split('_')[0] >= last_processed_match_date.strftime('%Y-%m-%d')])

    for file in files_list:
        source_file_dir = BRONZE_DATASETS_DIR / 'riot_api' / file
        if not os.path.exists(source_file_dir):
            raise ValueError(f"The source file {file} does not exist. Please check the data source.")

        #Extract id from metadata and added to the info DataFrame
        base = pd.read_json(source_file_dir, lines=True)
        base_ids = base['metadata'].map(lambda x: x['matchId'])
        base_df = pd.json_normalize(base['info'].tolist(), sep = "_")
        base_df.insert(0, 'match_id', base_ids)

        #Execute the processing functions for matches summary and ban list
        ban_list_df = process_soloq_ban_list(base_df, rewrite)
        matches_summary_df = process_soloq_match_summary(base_df, rewrite)

        if ban_list_df.empty or matches_summary_df.empty:
            raise ValueError(f"No new matches or ban list data to process for file {file}. Please check the data source.")

        #Create parquets
        try:
            matches_summary_df.to_parquet(SOLOQ_MATCHES_SUMMARY_FILE, engine='pyarrow', index=False)
            ban_list_df.to_parquet(SOLOQ_MATCHES_BAN_LIST_FILE, engine='pyarrow', index=False)
        except Exception as e:
            raise ValueError(f"Failed to write the matches summary or ban list DataFrame to Parquet format. Please check the data and try again. Error: {e}")

    #Update last match date in the database
    r = metadata.update_last_match_date("soloq", matches_summary_df['date'].max())
    if not r:
        raise ValueError("Failed to update the last match date in the metadata database.")

    return True


def process_soloq_ban_list(base_df: pd.DataFrame, rewrite=False) -> pd.DataFrame:
    ban_source_columns = ['match_id','gameStartTimestamp','gameVersion','teams']
    ban_list_columns = ['date', 'patch', 'match_id', 'side', 'ban']
    champions_dimension = pd.read_parquet(CHAMPIONS_DIMENSION_FILE, engine='pyarrow')

    if champions_dimension.empty:
        raise ValueError("Champions dimension DataFrame is empty. Please check the champions dimension parquet file.")

    ###Get ban list parquet files or create empty DataFrames if I will rewrite the data
    if os.path.exists(SOLOQ_MATCHES_BAN_LIST_FILE) and rewrite == False:
        ban_list_df = pd.read_parquet(SOLOQ_MATCHES_BAN_LIST_FILE, engine='pyarrow')
    else:
        ban_list_df = pd.DataFrame(columns=ban_list_columns)

    ban_base = (base_df.loc[:, ban_source_columns]
                .explode('teams').reset_index(drop=True).assign(
                    date=lambda x: pd.to_datetime(x['gameStartTimestamp'], unit='ms'),
                    patch=lambda x: x['gameVersion'].map(lambda y: '.'.join(y.split('.')[:2])),
                    gameid=lambda x: x['match_id'],
                    side=lambda x: x['teams'].map(lambda y: 'Blue' if y['teamId'] == 100 else 'Red'),
                    bans=lambda x: x['teams'].map(lambda y: [str(b['championId']) for b in y['bans']]),
                ).drop(columns=['teams','gameStartTimestamp','gameVersion','match_id']))

    unlist_bans = (ban_base['bans'].apply(lambda x: x if isinstance(x,list) else [])
                    .apply(lambda x: pd.Series(x[:], index=[f'ban{i+1}' for i in range(0,5)])))
    ban_base = pd.concat([ban_base.drop(columns=['bans']), unlist_bans], axis=1)
    ban_melted = (
        ban_base.melt(
            id_vars=['date','patch','gameid','side'],
            value_vars=[f'ban{i+1}' for i in range(0,5)],
            var_name='ban_number',
            value_name='ban'
        ).drop(columns=['ban_number']).dropna(subset=['ban'])
    )

    ban_list_melted = (ban_melted.merge(champions_dimension, how='left', left_on='ban', right_on='championId')
        .drop(columns=['championId', 'ban']).rename(columns={'championName': 'ban'}).dropna(subset=['ban']))
    ban_list_df = pd.concat([ban_list_df, ban_list_melted], ignore_index=True)
    
    return ban_list_df

def process_soloq_match_summary(base_df: pd.DataFrame, rewrite=False) -> pd.DataFrame:
    champion_info_columns = ['championName', 'teamId', 'teamPosition', 'win', 'gameEndedInSurrender',
                         'kills','deaths','assists',
                         'totalDamageDealtToChampions', 'totalDamageTaken',
                         'doubleKills','tripleKills','quadraKills','pentaKills',
                         'longestTimeSpentLiving', 'largestKillingSpree', 'largestMultiKill',
                         'totalMinionsKilled']
    match_info_columns = ['match_id', 'gameVersion', 'gameCreation', 'gameDuration', 'participants']
    match_summary_columns = ['match_id','date','duration','patch','side','position','champion','gamelength','result',
                             'kills','deaths','assists',
                             'teamkills','teamdeaths',
                             'doublekills','triplekills','quadrakills','pentakills',
                             'damagetochampions', 'damagetaken',
                             'longesttimespentliving', 'largestkillingspree', 'largestmultikill',
                             'totalcs']

    ##Get matches parquet files or create empty DataFrames if I will rewrite the data
    if os.path.exists(SOLOQ_MATCHES_SUMMARY_FILE) and rewrite == False:
        matches_summary_df = pd.read_parquet(SOLOQ_MATCHES_SUMMARY_FILE, engine='pyarrow')
    else:
        matches_summary_df = pd.DataFrame(columns=match_summary_columns)
    

    match_df = (base_df.loc[base_df['endOfGameResult'] == 'GameComplete', match_info_columns]
                .assign(
                    patch=lambda x: x['gameVersion'].map(lambda y: '.'.join(y.split('.')[:2])),
                    date=lambda x: pd.to_datetime(x['gameCreation'], unit='ms'),
                    duration=lambda x: pd.to_timedelta(x['gameDuration'], unit='s')
                )
                .drop(columns=['gameVersion','gameCreation','gameDuration'])
                .explode('participants').reset_index(drop=True)
    )

    champion_info_df = pd.json_normalize(match_df['participants']).loc[:, champion_info_columns].copy()
    champion_info_df = (pd.concat([match_df, champion_info_df], axis=1, ignore_index=False)
                        .assign(
                            teamkills=lambda x: x.groupby(['match_id', 'teamId'])['kills'].transform('sum'),
                            teamdeaths=lambda x: x.groupby(['match_id', 'teamId'])['deaths'].transform('sum'),
                            side = lambda x: x['teamId'].map(lambda y: 'Blue' if y == 100 else 'Red')
                        )
                        .drop(columns=['participants','teamId'])
                        .rename(columns={'championName': 'champion', 'teamPosition': 'position', 'win': 'result',
                                         'totalDamageDealtToChampions': 'damagetochampions', 'totalDamageTaken': 'damagetaken',
                                         'doubleKills': 'doublekills', 'tripleKills': 'triplekills', 'quadraKills': 'quadrakills', 'pentaKills': 'pentakills',
                                         'longestTimeSpentLiving': 'longesttimespentliving', 'largestKillingSpree': 'largestkillingspree', 'largestMultiKill': 'largestmultikill',
                                         'totalMinionsKilled': 'totalcs'
                        })
    )
    matches_summary_df = pd.concat([matches_summary_df, champion_info_df], ignore_index=True)

    return matches_summary_df


# def get_last_match_date(type: str) -> pd.Timestamp | None: ##Replaced by metadata
#     if type == 'pro':
#         file_path = PRO_MATCHES_SUMMARY_FILE
#     elif type == 'soloq':
#         file_path = SOLOQ_MATCHES_SUMMARY_FILE
#     else:
#         raise ValueError(f"Unknown match type: {type}")

#     if not os.path.exists(file_path):
#         return None
#     else:
#         matches = pd.read_parquet(file_path, engine='pyarrow')
#         if matches.empty:
#             return None
#         else:
#             last_match_date = matches['date'].max()
#             return last_match_date