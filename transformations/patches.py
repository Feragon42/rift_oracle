import pandas as pd
import os
from transformations.utils import PATCHES_DIMENSION_FILE, CHAMPIONS_CHANGES_DIMENSION_FILE, SILVER_DATASETS_DIR, BRONZE_DATASETS_DIR

def upload_patches_dimension(rewrite=False):
    patches_desc_df = pd.read_csv(BRONZE_DATASETS_DIR / 'patches/scraped_patch_notes.csv')

    if os.path.exists(PATCHES_DIMENSION_FILE) and rewrite == False:
        patches_dimension = pd.read_parquet(PATCHES_DIMENSION_FILE, engine='pyarrow')
    else:
        patches_dimension = pd.DataFrame(columns=['patch_number', 'patch_start_date', 'patch_end_date', 'patch_url'])

    # First validations
    if patches_desc_df.empty:
        raise ValueError("The scraped_patch_notes.csv file is empty. Please check the data source.")
    else:
        if patches_desc_df['patch_date'].isnull().any() or patches_desc_df['patch_number'].isnull().any() or patches_desc_df['patch_url'].isnull().any():
            raise ValueError("The 'patch_date', 'patch_number', or 'patch_url' column contains null values. Please check the data source.")

    #Complete dates from the source
    try:
        patches_desc_df['patch_start_date'] = pd.to_datetime(patches_desc_df['patch_date'], format='%m/%d/%Y', errors='coerce')
        patches_desc_df = patches_desc_df.sort_values(by='patch_start_date', ascending=True)
        patches_desc_df['patch_end_date'] = patches_desc_df['patch_start_date'].shift(-1)
    except Exception as e:
        raise ValueError(f"An error occurred while converting 'patch_date' to datetime: {e}")

    # Add the new patches to the patches dimension DataFrame (If rewrite it will add all patches from the source)
    for patch in patches_desc_df.itertuples():
        if patch.patch_number not in patches_dimension['patch_number'].values:
            new_patch = pd.DataFrame({
                'patch_number': [patch.patch_number],
                'patch_start_date': [patch.patch_start_date],
                'patch_end_date': [patch.patch_end_date],
                'patch_url': [patch.patch_url]
            })
            patches_dimension = pd.concat([patches_dimension, new_patch], ignore_index=True)

    #Save the patches dimension DataFrame to a Parquet file
    try:
        patches_dimension.to_parquet(PATCHES_DIMENSION_FILE, engine='pyarrow', index=False)
    except Exception as e:
        raise ValueError(f"Failed to write the patches dimension DataFrame to Parquet format. Please check the data and try again. Error: {e}")

    return True

def upload_champions_changes_dimension(rewrite=False):

    #Load the patches dimension DataFrame
    if not os.path.exists(PATCHES_DIMENSION_FILE):
        raise ValueError("The patches_dimension.parquet file does not exist. Please check the data source.")
    else:
        patches = pd.read_parquet(PATCHES_DIMENSION_FILE, engine='pyarrow')
        if patches.empty:
            raise ValueError("The patches_dimension.parquet file is empty. Please check the data source.")

    #Load existing champions changes dimension DataFrame or create a new one if it doesn't exist (if rewrite is true, it will create a new one nonetheless)
    if not os.path.exists(CHAMPIONS_CHANGES_DIMENSION_FILE) and rewrite == False:
        champions_changes = pd.DataFrame(columns=['patch_number', 'champion_name', 'change_type'])
    else:
        champions_changes = pd.read_parquet(CHAMPIONS_CHANGES_DIMENSION_FILE, engine='pyarrow')

    not_existing_patch_files = pd.DataFrame(columns=['patch_number', 'processing_date'])
    for patch in patches.itertuples():
        ##Find the patch highlights champion changes file for the current patch number and append it to the champions_changes DataFrame if it exists, otherwise log the patch number in not_existing_patch_files DataFrame
        if patch.patch_number not in champions_changes['patch_number'].values:
            source_file = BRONZE_DATASETS_DIR / f'patches/patch_highlights_champion_changes_{patch.patch_number}.csv'
            if os.path.exists(source_file):
                source_file_data = pd.read_csv(source_file)
                new_changes = pd.DataFrame({
                    'patch_number': source_file_data['Patch Number'],
                    'champion_name': source_file_data['Champion'],
                    'change_type': source_file_data['Change Type']
                })
                champions_changes = pd.concat([champions_changes, new_changes], ignore_index=True)
            else:
                not_existing_patch_files = pd.concat([not_existing_patch_files, pd.DataFrame({'patch_number': [patch.patch_number], 'processing_date': [pd.Timestamp.now()]})], ignore_index=True)

    #Save the champions_changes DataFrame to a Parquet file
    try:
        champions_changes.to_parquet(CHAMPIONS_CHANGES_DIMENSION_FILE, engine='pyarrow', index=False)
    except Exception as e:
        raise ValueError(f"Failed to write the champions changes dimension DataFrame to Parquet format. Please check the data and try again. Error: {e}")

    #If there were any patch numbers that did not have a corresponding patch highlights champion changes file, save them to a CSV file in the errors directory
    if not not_existing_patch_files.empty:
        os.makedirs(SILVER_DATASETS_DIR / 'errors', exist_ok=True)
        not_existing_patch_files.to_csv(SILVER_DATASETS_DIR / 'errors' / f'not_existing_patch_files_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv', index=False)

    return True


def get_patch_dates(patch_number: int | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
    if not os.path.exists(PATCHES_DIMENSION_FILE):
        raise ValueError("The patches_dimension.parquet file does not exist. Please check the data source.")
    else:
        patches = pd.read_parquet(PATCHES_DIMENSION_FILE, engine='pyarrow')
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