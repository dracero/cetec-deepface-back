
from asyncio import tasks
from datetime import datetime, timedelta
from textwrap import dedent

from airflow import DAG
from airflow.operators.python import PythonOperator

from pymongo import MongoClient
from deepface import DeepFace
import base64

#def _get_attendance():
#    client = MongoClient('mongodb://euge:1234@cluster0-shard-00-00.b2f7j.mongodb.net:27017,cluster0-shard-00-01.b2f7j.mongodb.net:27017,cluster0-shard-00-02.b2f7j.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-dw8ukd-shard-0&authSource=admin&retryWrites=true&w=majority')
#    db = client["myFirstDatabase"]
#    col = db["attendance"]
#    return list(col.find())

def _validate(ti):
    client = MongoClient('mongodb://euge:1234@cluster0-shard-00-00.b2f7j.mongodb.net:27017,cluster0-shard-00-01.b2f7j.mongodb.net:27017,cluster0-shard-00-02.b2f7j.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-dw8ukd-shard-0&authSource=admin&retryWrites=true&w=majority')
    db = client["myFirstDatabase"]
    col_attendance = db["attendance"]
    col_students = db["students"]
    attendees = col_attendance.find()
    
    for attendee in attendees:
        course = attendee['course']
        students = col_students.find({'course': course, 'state':{'$exists':False}})
        
        for student in students:
            result = DeepFace.verify([[attendee['photo'], student['photo']]],
                                    model_name = "VGG-Face",
                                    distance_metric = "cosine",
                                    detector_backend = "opencv"
            )
            if result["pair_1"]["verified"]:
                col_students.update_one({'_id':student['_id']}, {"$set":{'state':'presente'}})
                break

def _complete_attendance():
    client = MongoClient('mongodb://euge:1234@cluster0-shard-00-00.b2f7j.mongodb.net:27017,cluster0-shard-00-01.b2f7j.mongodb.net:27017,cluster0-shard-00-02.b2f7j.mongodb.net:27017/myFirstDatabase?ssl=true&replicaSet=atlas-dw8ukd-shard-0&authSource=admin&retryWrites=true&w=majority')
    db = client["myFirstDatabase"]
    col_students = db["students"]
    for student in col_students.find({'state':{'$exists':False}}):
        col_students.update_one({'_id':student['_id']}, {"$set":{'state':'ausente'}})
    return 'verified'
    

with DAG(
    'Deepface',
    default_args={
        'depends_on_past': False,
        'email': ['airflow@example.com'],
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='Compare faces with Deepface',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=['example'],
) as dag:
    
    validate = PythonOperator(
        task_id = 'validate',
        python_callable=_validate
    )
    
    complete_attendance = PythonOperator(
        task_id = 'complete_attendance',
        python_callable=_complete_attendance
    )

    validate >> complete_attendance

