from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
from pymongo import MongoClient
from deepface import DeepFace

PRESENT = 'presente'
LATE = 'tarde'

def _validate():
    client = MongoClient(Variable.get("MONGO_URL"))
    db = client["myFirstDatabase"]
    col_attendances = db["attendances"]
    col_students = db["students"]
    col_verified = db["verified_attendances"]
    col_exams = db["exams"]
    attendees = col_attendances.find()
    
    for attendee in attendees:
        student = col_students.find_one({'email':attendee['email']})
        if not student:
            continue
        
        result = DeepFace.verify([[attendee['image'], student['photo']]],
                                model_name = "VGG-Face",
                                distance_metric = "cosine",
                                detector_backend = "opencv"
        )
        if not result["pair_1"]["verified"]:
            continue

        exam = col_exams.find_one({'course':attendee['course']})
        if not exam:
            continue

        start_max_margin = exam['start'] + timedelta(minutes=exam['startMinutesMargin'])
        start_min_margin = exam['start'] - timedelta(minutes=exam['startMinutesMargin'])
        if start_min_margin <= attendee['date'] <= start_max_margin:
            state = PRESENT
        else:
            state = LATE
        col_verified.insert_one({'email': attendee['email'], 'course':attendee['course'], 'state':state, 'date':attendee['date']})

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

    validate

