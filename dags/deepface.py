from email.message import EmailMessage
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
from pymongo import MongoClient
from deepface import DeepFace
import smtplib

PRESENT = 'presente'
LATE = 'tarde'
EXAM_DATE_MINUTES_MARGIN = 60
EXAM_EARLY_MARGIN = 30

def move_date(date, move_minutes):
    return date + timedelta(minutes=move_minutes)

def get_margin_limits(start, minutes_margin):
    begin_margin = move_date(start, -minutes_margin)
    end_margin = move_date(start, minutes_margin)
    return (begin_margin, end_margin)

def find_exam(col_exams, course, start, minutes_margin):
    begin_margin, end_margin = get_margin_limits(start, minutes_margin)
    return col_exams.find_one({'course':course, 'start' : {'$gte': begin_margin, '$lt': end_margin}})

def is_same_person(image1, image2):
    result = DeepFace.verify([[image1, image2]],
                            model_name = "VGG-Face",
                            distance_metric = "cosine",
                            detector_backend = "opencv"
    )
    return result["pair_1"]["verified"]

def is_on_time(date, start):
    early_margin = move_date(start, -EXAM_EARLY_MARGIN)
    return (early_margin <= date <= start)

def is_late(date, start, minutes_margin):
    late_margin = move_date(start, minutes_margin)
    return (start < date <= late_margin)

def _validate():
    client = MongoClient(Variable.get("MONGO_URL"))
    db = client["myFirstDatabase"]
    col_attendances = db["attendances"]
    col_students = db["students"]
    col_verified = db["verified_attendances"]
    col_exams = db["exams"]
    not_verified = []
    
    attendees = col_attendances.find()
    for attendee in attendees:
        student = col_students.find_one({'email':attendee['email']})
        if not student:
            continue

        exam = find_exam(col_exams, attendee['course'], attendee['date'], EXAM_DATE_MINUTES_MARGIN)
        if not exam:
            continue

        if not is_same_person(attendee['image'], student['image']):
            not_verified.append((student['name'], student['email']))
            continue

        if is_on_time(attendee['date'], exam['start']):
            state = PRESENT
        elif is_late(attendee['date'], exam['start'], exam['startMinutesMargin']):
            state = LATE

        col_verified.insert_one({'email':attendee['email'], 'course':attendee['course'], 'state':state, 'date':attendee['date'], 'image':attendee['image']})
        col_attendances.delete_one({'_id':attendee['_id']})

    
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
    schedule_interval=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=['example'],
) as dag:
    
    validate = PythonOperator(
        task_id = 'validate',
        python_callable=_validate
    )

    validate

