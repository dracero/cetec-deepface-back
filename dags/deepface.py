
from asyncio import tasks
from datetime import datetime, timedelta
from textwrap import dedent

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator

from pymongo import MongoClient
from deepface import DeepFace
import base64

def _get_photos():
    client = MongoClient('mongodb://euge:1234@cluster0-shard-00-00.b2f7j.mongodb.net:27017,cluster0-shard-00-01.b2f7j.mongodb.net:27017,cluster0-shard-00-02.b2f7j.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-dw8ukd-shard-0&authSource=admin&retryWrites=true&w=majority')
    db = client["myFirstDatabase"]
    col = db["fotos"]

    img1 = col.find_one({"email": "aj1@mail.com"})["photo"]
    img2 = col.find_one({"email": "aj2@mail.com"})["photo"]
    img3 = col.find_one({"email": "bp@mail.com"})["photo"]
    
    return [img1, img2, img3]

def _validate(ti):
    imgs = ti.xcom_pull(task_ids=['get_photos'])[0]
    result = DeepFace.verify([[imgs[0], imgs[1]]],
				  model_name = "VGG-Face",
				  distance_metric = "cosine",
				  detector_backend = "opencv"
    )
    verified = result["pair_1"]["verified"]
    if (verified):
        return 'verified'
    return 'not_verified'

with DAG(
    'Deepface',
    # These args will get passed on to each operator
    # You can override them on a per-task basis during operator initialization
    default_args={
        'depends_on_past': False,
        'email': ['airflow@example.com'],
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        # 'queue': 'bash_queue',
        # 'pool': 'backfill',
        # 'priority_weight': 10,
        # 'end_date': datetime(2016, 1, 1),
        # 'wait_for_downstream': False,
        # 'sla': timedelta(hours=2),
        # 'execution_timeout': timedelta(seconds=300),
        # 'on_failure_callback': some_function,
        # 'on_success_callback': some_other_function,
        # 'on_retry_callback': another_function,
        # 'sla_miss_callback': yet_another_function,
        # 'trigger_rule': 'all_success'
    },
    description='Compare faces with Deepface',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=['example'],
) as dag:
    
    get_photos = PythonOperator(
        task_id = 'get_photos',
        python_callable=_get_photos
    )
    
    validate = BranchPythonOperator(
        task_id = 'validate',
        python_callable=_validate
    )

    verified = BashOperator(
        task_id='verified',
        bash_command="echo 'verified'",
    )
    
    not_verified = BashOperator(
        task_id='not_verified',
        bash_command="echo 'NOT verified'",
    )

    get_photos >> validate >> [verified, not_verified]
