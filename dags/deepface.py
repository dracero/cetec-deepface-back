from email.message import EmailMessage
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from datetime import datetime, timedelta
from pymongo import MongoClient
from deepface import DeepFace
import smtplib

from email.message import EmailMessage

PRESENT = 'presente'
LATE = 'tarde'
EXAM_DATE_MINUTES_MARGIN = 60
EXAM_EARLY_MARGIN = 3
SUCCESS_SUBJECT = 'Alumnos verificados correctamente'
SUCCESS_BODY = 'Todos los alumnos han sido reconocidos. No es necesario verificar la asistencia.'
FAIL_SUBJECT = 'Verificar alumnos'
FAIL_BODY = 'Los siguientes alumnos no fueron reconocidos correctamente. Por favor, verifique su asistencia:\n'

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
                            detector_backend = "opencv",
                            enforce_detection= False
    )
    return result["pair_1"]["verified"]

def is_on_time(date, start, minutes_margin):
    early_margin = move_date(start, -EXAM_EARLY_MARGIN)
    late_margin = move_date(start, minutes_margin)
    return (early_margin <= start <= date <= late_margin)

def is_late(date, start, minutes_margin):
    late_margin = move_date(start, minutes_margin)
    return (start < late_margin < date)

def notify_unvalidated(not_verified):
    user = Variable.get("EMAIL_USER")
    pwd = Variable.get("EMAIL_PASSWORD")

    if not bool(not_verified):
        SUBJECT = SUCCESS_SUBJECT
        TEXT = SUCCESS_BODY
    else:
        SUBJECT = FAIL_SUBJECT
        TEXT = FAIL_BODY
        for name,email in not_verified:
            TEXT += '     - ' + name + ' - ' + email + '\n'

    recipient = "diego.racero@ing-racero.com.ar"
    
    FROM = user
    TO = recipient if isinstance(recipient, list) else [recipient]
    
    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server_ssl = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server_ssl.ehlo() # optional, called by login()
        server_ssl.login(user, pwd)  
        # ssl server doesn't support or need tls, so don't call server_ssl.starttls() 
        server_ssl.sendmail(FROM, TO, message)
        #server_ssl.quit()
        server_ssl.close()
        print ('successfully sent the mail')
    except:
        print ("failed to send mail")
 

def _validate():
    client = MongoClient(Variable.get("MONGO_URL"))
    db = client["test"]
    col_attendances = db["attendances"]
    col_students = db["students"]
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
            col_attendances.delete_one({'_id':attendee['_id']})
            continue

        state = ''
        if is_on_time(attendee['date'], exam['start'], exam['startMinutesMargin']):
            state = PRESENT
        elif is_late(attendee['date'], exam['start'], exam['startMinutesMargin']):
            state = LATE
        else:
            col_attendances.delete_one({'_id':attendee['_id']})
            continue

        newAttendance = {'date':attendee['date'], 'course':attendee['course'], 'state':state}
        col_students.find_one_and_update(
            { 'email': attendee['email'] },
            { '$push': { 'attendances': newAttendance } },
            { 'upsert': True }
        )
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

