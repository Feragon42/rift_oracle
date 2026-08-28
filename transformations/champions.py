import pandas as pd
import os
from transformations.utils import CHAMPIONS_DIMENSION_FILE, SOLOQ_MATCHES_SUMMARY_FILE

def update_champions_dimension():
    #Instead of using DDragon, I can create my own champions dimension from the matches data

    df = (pd.read_parquet(SOLOQ_MATCHES_SUMMARY_FILE)
          .loc[:, ['champion','champion_id']]
          .drop_duplicates(subset=['champion','champion_id'],keep='first')
    )

    df.to_parquet(CHAMPIONS_DIMENSION_FILE, engine='pyarrow', index=False)