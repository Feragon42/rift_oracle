from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'silver'
BRONZE_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze'

## Patches
PATCHES_DIMENSION_FILE = SILVER_DATASETS_DIR / 'patches_dimension.parquet'
CHAMPIONS_CHANGES_DIMENSION_FILE = SILVER_DATASETS_DIR / 'champions_changes_dimension.parquet'

## Matches
PRO_MATCHES_SUMMARY_FILE = SILVER_DATASETS_DIR / 'pro_matches_summary.parquet'
SOLOQ_MATCHES_SUMMARY_FILE = SILVER_DATASETS_DIR / 'soloq_matches_summary.parquet'
PRO_MATCHES_BAN_LIST_FILE = SILVER_DATASETS_DIR / 'pro_matches_ban_list.parquet'
SOLOQ_MATCHES_BAN_LIST_FILE = SILVER_DATASETS_DIR / 'soloq_matches_ban_list.parquet'

##Champions
CHAMPIONS_DIMENSION_FILE = SILVER_DATASETS_DIR / 'champions_dimension.parquet'