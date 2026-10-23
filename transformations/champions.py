import pandas as pd
import os
from transformations.utils import CHAMPIONS_DIMENSION_FILE, \
    SOLOQ_MATCHES_SUMMARY_FILE, PRO_MATCHES_SUMMARY_FILE, PRO_MATCHES_BAN_LIST_FILE, SOLOQ_MATCHES_BAN_LIST_FILE, \
    CHAMPIONS_PICK_STATS_FILE, CHAMPIONS_DIMENSION_FILE, CHAMPIONS_CHANGES_GOLD

def update_champions_dimension():
    #Instead of using DDragon, I can create my own champions dimension from the matches data

    ##I add alt names because in the API DF Riot simplify it champions names, 
    # but in the competitive DF OE uses the real full name
    champions_alt_names = {"Khazix": "Kha'Zix",  "KogMaw": "Kog'Maw",  "Velkoz": "Vel'Koz",  
                           "RekSai": "Rek'Sai", "Chogath": "Cho'Gath",   "Kaisa": "Kai'Sa", 
                           "Belveth": "Bel'Veth",  "KSante": "K'Sante", "MonkeyKing": "Wukong"}

    df = (pd.read_parquet(SOLOQ_MATCHES_SUMMARY_FILE)
          .loc[:, ['champion','champion_id']]
          .drop_duplicates(subset=['champion','champion_id'],keep='first')
          .assign(
              champion_real_name = lambda x: x['champion'].replace(champions_alt_names)
          )
    )

    df.to_parquet(CHAMPIONS_DIMENSION_FILE, engine='pyarrow', index=False)

def build_ban_list_gold():
    #Import data files
    df_pro_ban = pd.read_parquet(PRO_MATCHES_BAN_LIST_FILE)
    df_soloq_ban = pd.read_parquet(SOLOQ_MATCHES_BAN_LIST_FILE)
    df_pro_matches = pd.read_parquet(PRO_MATCHES_SUMMARY_FILE)
    df_soloq_matches = pd.read_parquet(SOLOQ_MATCHES_SUMMARY_FILE)
    champions_dimension_df = pd.read_parquet(CHAMPIONS_DIMENSION_FILE)

    #Check if data files exist and are not empty before proceeding
    if not os.path.exists(PRO_MATCHES_BAN_LIST_FILE) or not os.path.exists(SOLOQ_MATCHES_BAN_LIST_FILE) or not os.path.exists(PRO_MATCHES_SUMMARY_FILE) or not os.path.exists(SOLOQ_MATCHES_SUMMARY_FILE):
        raise ValueError("One or more of the required data files do not exist. Please check the data source.")
    elif df_pro_ban.empty or df_soloq_ban.empty or df_pro_matches.empty or df_soloq_matches.empty:
        raise ValueError("One or more of the required data files are empty. Please check the data source.")

    #Calculate total matches per patch for pro and soloq matches
    pro_matches_total_match_per_patch = (df_pro_matches.groupby('patch').agg(matches=('gameid', 'nunique')).reset_index())
    soloq_matches_total_match_per_patch = (df_soloq_matches.groupby('patch').agg(matches=('match_id', 'nunique')).reset_index())

    #Create a df for pick and ban rates per champion per patch
    pro_pick_rate_df = (
        df_pro_matches
        .groupby(['patch', 'champion'])
        .agg(
            pro_pick_amt=('gameid', 'nunique')
        )
        .reset_index()
        .assign(
            pro_pick_rate=lambda x: x['pro_pick_amt'] / x['patch'].map(pro_matches_total_match_per_patch.set_index('patch')['matches']),
            champion_real_name = lambda x: x['champion'].map(champions_dimension_df.set_index('champion')['champion_real_name']).fillna(x['champion'])
        )
        .drop(columns=['champion'])
        .rename(columns={"champion_real_name": "champion"})
        .reset_index(drop=True)
    )

    pro_ban_rate_df = (
        df_pro_ban
        .groupby(['patch', 'ban'])
        .agg(
            pro_ban_amt=('gameid', 'nunique')
        )
        .reset_index()
        .assign(
            pro_ban_rate=lambda x: x['pro_ban_amt'] / x['patch'].map(pro_matches_total_match_per_patch.set_index('patch')['matches']),
            champion_real_name = lambda x: x['ban'].map(champions_dimension_df.set_index('champion')['champion_real_name']).fillna(x['ban']),
        )
        .rename(columns={"champion_real_name": "champion"})
        .drop(columns=['ban'])
    )

    soloq_pick_rate_df = (
        df_soloq_matches
        .groupby(['patch', 'champion'])
        .agg(
            soloq_pick_amt=('match_id', 'nunique')
        )
        .reset_index()
        .assign(
            soloq_pick_rate=lambda x: x['soloq_pick_amt'] / x['patch'].map(soloq_matches_total_match_per_patch.set_index('patch')['matches']),
            champion_real_name = lambda x: x['champion'].map(champions_dimension_df.set_index('champion')['champion_real_name']).fillna(x['champion'])
        )
        .drop(columns=['champion'])
        .rename(columns={"champion_real_name": "champion"})
        .reset_index(drop=True)
    )

    soloq_ban_rate_df = (
        df_soloq_ban
        .groupby(['patch', 'ban'])
        .agg(
            soloq_ban_amt=('gameid', 'nunique')
        )
        .reset_index()
        .assign(
            soloq_ban_rate=lambda x: x['soloq_ban_amt'] / x['patch'].map(soloq_matches_total_match_per_patch.set_index('patch')['matches']),
            champion_real_name = lambda x: x['ban'].map(champions_dimension_df.set_index('champion')['champion_real_name']).fillna(x['ban']),
        )
        .rename(columns={"champion_real_name": "champion"})
        .drop(columns=['ban'])
    )

    #Consolidate into a single DataFrame for easier analysis
    stats_columns = ['pro_pick_rate', 'pro_pick_amt', 'pro_ban_rate', 'pro_ban_amt', 
                     'soloq_pick_rate', 'soloq_pick_amt', 'soloq_ban_rate', 'soloq_ban_amt']

    patch_champion_base = pd.read_parquet(CHAMPIONS_CHANGES_GOLD)[['patch', 'champion']]

    consolidated_pick_stats_df = (
        patch_champion_base
        .merge(pro_pick_rate_df, on=['patch', 'champion'], how='outer')
        .merge(pro_ban_rate_df, on=['patch', 'champion'], how='outer')
        .merge(soloq_pick_rate_df, on=['patch', 'champion'], how='outer')
        .merge(soloq_ban_rate_df, on=['patch', 'champion'], how='outer')
        .fillna({col: 0 for col in stats_columns})
        .pipe(lambda x: x[['patch', 'champion', *x.columns.difference(['patch', 'champion'], sort=False)]])
    )

    try:
        consolidated_pick_stats_df.to_parquet(CHAMPIONS_PICK_STATS_FILE, engine='pyarrow', index=False)
    except Exception as e:
        print(f"Error saving consolidated pick stats: {e}")