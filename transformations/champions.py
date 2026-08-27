import pandas as pd
import os
from utils import CHAMPIONS_DIMENSION_FILE, SOLOQ_MATCHES_SUMMARY_FILE

def update_champions_dimension(rewrite=False):
    #Instead of using DDragon, I can create my own champions dimension from the matches data

    x = base_df.loc[:, ['participants']]
    y = x.explode('participants').reset_index(drop=True).assign(
        championId=lambda x: x['participants'].map(lambda y: str(y['championId']) if isinstance(y, dict) and 'championId' in y else None),
        championName=lambda x: x['participants'].map(lambda y: y['championName'] if isinstance(y, dict) and 'championName' in y else None)
    ).drop_duplicates(subset=['championId','championName'], keep='first').drop(columns=['participants']).dropna()
    print(y.count())
    y.head(10)

    y.to_parquet(SILVER_DATASETS_DIR / 'champions_dimension.parquet', engine='pyarrow', index=False)