from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'silver'
BRONZE_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze'
GOLD_DATASET_DIR = PROJECT_ROOT / 'datasets' / 'gold'

## Patches
PATCHES_DIMENSION_FILE = SILVER_DATASETS_DIR / 'patches_dimension.parquet'
CHAMPIONS_CHANGES_DIMENSION_FILE = SILVER_DATASETS_DIR / 'champions_changes_dimension.parquet'
CHAMPIONS_CHANGES_GOLD = GOLD_DATASET_DIR / 'champions_changes_dimension.parquet'
alternative_patch_numbers_change = {'2025':'25', '25.S1.1': '25.1', '25.S1.2' : '25.2', '25.03': '25.3', 
                                    '25.04': '25.4', '25.05': '25.5','25.06': '25.6', '25.07': '25.7', 
                                    '25.08': '25.8', '25.09': '25.9'}

## Matches
PRO_MATCHES_SUMMARY_FILE = SILVER_DATASETS_DIR / 'pro_matches_summary.parquet'
SOLOQ_MATCHES_SUMMARY_FILE = SILVER_DATASETS_DIR / 'soloq_matches_summary.parquet'
PRO_MATCHES_BAN_LIST_FILE = SILVER_DATASETS_DIR / 'pro_matches_ban_list.parquet'
SOLOQ_MATCHES_BAN_LIST_FILE = SILVER_DATASETS_DIR / 'soloq_matches_ban_list.parquet'
PATCH_MATCHES_SUMMARY_FILE = GOLD_DATASET_DIR / 'patch_matches_summary.parquet'

##Champions
CHAMPIONS_DIMENSION_FILE = SILVER_DATASETS_DIR / 'champions_dimension.parquet'
CHAMPIONS_PICK_STATS_FILE = GOLD_DATASET_DIR / 'champions_pick_stats.parquet'
PATCH_TOP_PICK_RATE_FILE = GOLD_DATASET_DIR / 'patch_top_pick_rate.parquet'

##Analytics
CHAMPIONS_CHANGES_ANALYTICS_FILE = GOLD_DATASET_DIR / 'champions_changes_analytics.parquet'
MODEL_FILE = GOLD_DATASET_DIR / 'model.pkl'