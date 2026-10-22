import pandas as pd
import os
from transformations.utils import CHAMPIONS_DIMENSION_FILE, SOLOQ_MATCHES_SUMMARY_FILE

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