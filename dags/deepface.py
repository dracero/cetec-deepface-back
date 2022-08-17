from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
from pymongo import MongoClient
from deepface import DeepFace

import smtplib
from email.message import EmailMessage

PRESENT = 'presente'
EXAM_DATE_MINUTES_MARGIN = 60
SUCCESS_SUBJECT = 'Alumnos verificados correctamente'
SUCCESS_BODY = 'Todos los alumnos han sido reconocidos. No es necesario verificar la asistencia.'
FAIL_SUBJECT = 'Verificar alumnos'
FAIL_BODY = 'Los siguientes alumnos no fueron reconocidos correctamente. Por favor, verifique su asistencia:\n'
            

def get_margin_limits(start, minutes_margin):
    start_min_margin = start - timedelta(minutes=minutes_margin)
    start_max_margin = start + timedelta(minutes=minutes_margin)
    return (start_min_margin, start_max_margin)

def find_exam(col_exams, course, start, minutes_margin):
    start_min_margin, start_max_margin = get_margin_limits(start, minutes_margin)
    return col_exams.find_one({'course':course, 'start' : {'$gte': start_min_margin, '$lt': start_max_margin}})

def is_same_person(image1, image2):
    result = DeepFace.verify([[image1, image2]],
                            model_name = "VGG-Face",
                            distance_metric = "cosine",
                            detector_backend = "opencv"
    )
    return result["pair_1"]["verified"]

def is_on_time(date, start, minutes_margin):
    start_min_margin, start_max_margin = get_margin_limits(start, minutes_margin)
    return (start_min_margin <= date <= start_max_margin)

def notify_unvalidated(not_verified):
    gmail_user = Variable.get("EMAIL_USER")
    gmail_password = Variable.get("EMAIL_PASSWORD")

    for mail,students_to_verify in not_verified.items():
        if not students_to_verify:
            subject = SUCCESS_SUBJECT
            body = SUCCESS_BODY
        else:
            subject = FAIL_SUBJECT
            body = FAIL_BODY
            for name,email in students_to_verify:
                body += '     - ' + name + ' - ' + email + '\n'

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = gmail_user
        msg['To'] = mail

        try:
            smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            smtp_server.ehlo()
            smtp_server.login(gmail_user, gmail_password)
            smtp_server.send_message(msg)
            smtp_server.close()

            print ("Email sent successfully!")

        except Exception as ex:

            print ("Something went wrong….",ex)

def _validate():
    client = MongoClient(Variable.get("MONGO_URL"))
    db = client["myFirstDatabase"]
    col_attendances = db["attendances"]
    col_students = db["students"]
    col_verified = db["verified_attendances"]
    col_exams = db["exams"]
    not_verified = {}
    
    attendees = col_attendances.find()
    for attendee in attendees:
        student = col_students.find_one({'email':attendee['email']})
        if not student:
            continue

        exam = find_exam(col_exams, attendee['course'], attendee['date'], EXAM_DATE_MINUTES_MARGIN)
        if not exam:
            continue

        if not is_same_person(attendee['image'], student['image']):
            info = (student['name'], student['email'])
            if exam['email'] not in not_verified.keys():
                not_verified[exam['email']] = []
            not_verified[exam['email']].append(info)
            continue

        if is_on_time(attendee['date'], exam['start'], exam['startMinutesMargin']):
            col_verified.insert_one({'email':attendee['email'], 'course':attendee['course'], 'state':PRESENT, 'date':attendee['date'], 'image':attendee['image']})
            col_attendances.delete_one({'_id':attendee['_id']})
    
    notify_unvalidated(not_verified)

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

