import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'silver'
BRONZE_DATASETS_DIR = PROJECT_ROOT / 'datasets' / 'bronze'

def create_patches_dimension():
    patches_desc_df = pd.read_csv(BRONZE_DATASETS_DIR / 'patches/scraped_patch_notes.csv')
    patches_dimension_dir = SILVER_DATASETS_DIR / 'patches_dimension.parquet'

    # First validations
    if patches_desc_df.empty:
        raise ValueError("The scraped_patch_notes.csv file is empty. Please check the data source.")
    else:
        if patches_desc_df['patch_date'].isnull().any() or patches_desc_df['patch_number'].isnull().any() or patches_desc_df['patch_url'].isnull().any():
            raise ValueError("The 'patch_date', 'patch_number', or 'patch_url' column contains null values. Please check the data source.")

    # Convert 'patch_date' to datetime format
    patches_desc_df['patch_start_date'] = pd.to_datetime(patches_desc_df['patch_date'], format='%m/%d/%Y', errors='coerce')

    # If any 'patch_date' values could not be converted to datetime, raise an error
    if patches_desc_df['patch_start_date'].isnull().any():
        raise ValueError("Some 'patch_date' values could not be converted to datetime. Please check the data source.")

    # Order the DataFrame by 'patch_start_date' to ensure correct end date assignment
    patches_desc_df = patches_desc_df.sort_values(by='patch_start_date', ascending=True)
    patches_desc_df['patch_end_date'] = patches_desc_df['patch_start_date'].shift(-1)

    
    result=patches_desc_df[['patch_number', 'patch_start_date', 'patch_end_date', 'patch_url']].to_parquet(patches_dimension_dir, engine='pyarrow', index=False)
    if result is None:
        raise ValueError("Failed to write the patches dimension DataFrame to Parquet format. Please check the data and try again.")

    return True