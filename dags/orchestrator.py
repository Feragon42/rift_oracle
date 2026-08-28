from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from ingestion.patch_scraping_functions import get_new_patch_notes
from ingestion.riot_api_functions import get_summoners_data, get_match_id_list, process_match_list
from ingestion.oe_functions import download_oe_data
from transformations.patches import upload_patches_dimension, upload_champions_changes_dimension
from transformations.matches import upload_oe_matches, upload_soloq_matches
from transformations.champions import update_champions_dimension

with DAG(
    dag_id="orchestrator",
    schedule=None,
    start_date=None,
    catchup=False,
) as dag:
    salutation = PythonOperator(
        task_id="salutation",
        python_callable=lambda: print("Hello World!"),
    )

    patch_scraping = PythonOperator(
        task_id="patch_scraping",
        python_callable=get_new_patch_notes,
    )

    summoners_data = PythonOperator(
        task_id="summoners_data",
        python_callable=get_summoners_data,
    )

    match_id_list = PythonOperator(
        task_id="match_id_list",
        python_callable=get_match_id_list,
    )

    process_match_list_task = PythonOperator(
        task_id="process_match_list",
        python_callable=process_match_list,
    )

    download_oe_data_task = PythonOperator(
        task_id="download_oe_data",
        python_callable=download_oe_data,
    )

    update_patches_dimension = PythonOperator(
        task_id="update_patches_dimension",
        python_callable=upload_patches_dimension,
    )

    update_champions_changes_dimension = PythonOperator(
        task_id="update_champions_changes_dimension",
        python_callable=upload_champions_changes_dimension,
    )

    transform_oe_matches = PythonOperator(
        task_id="transform_oe_matches",
        python_callable=upload_oe_matches,
    )

    transform_soloq_matches = PythonOperator(
        task_id="transform_soloq_matches",
        python_callable=upload_soloq_matches,
    )

    update_champions_dimension_task = PythonOperator(
        task_id="update_champions_dimension",
        python_callable=update_champions_dimension,
    )

    salutation >> [patch_scraping, summoners_data, download_oe_data_task] >> [update_patches_dimension] >> update_champions_dimension_task >> [transform_oe_matches, transform_soloq_matches]
    summoners_data >> match_id_list >> process_match_list_task
    update_patches_dimension >> update_champions_changes_dimension