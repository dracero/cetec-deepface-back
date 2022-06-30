from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
from pymongo import MongoClient
from deepface import DeepFace

PRESENT = 'presente'
ABSENT = 'ausente'

def _validate(ti):
    client = MongoClient(Variable.get("MONGO_URL"))
    db = client["myFirstDatabase"]
    col_attendance = db["attendance"]
    col_students = db["students"]
    attendees = col_attendance.find()
    
    for attendee in attendees:
        course = attendee['course']
        email = attendee['email']
        student = col_students.find_one({'email':email, 'course':course})
        
        result = DeepFace.verify([[attendee['photo'], student['photo']]],
                                model_name = "VGG-Face",
                                distance_metric = "cosine",
                                detector_backend = "opencv"
        )

        if result["pair_1"]["verified"]:
            col_students.update_one({'_id':student['_id']}, {"$set":{'state':PRESENT}})

def _complete_attendance():
    client = MongoClient(Variable.get("MONGO_URL"))
    db = client["myFirstDatabase"]
    col_students = db["students"]
    for student in col_students.find({'state':{'$exists':False}}):
        col_students.update_one({'_id':student['_id']}, {"$set":{'state':ABSENT}})
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

