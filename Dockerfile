FROM apache/airflow:2.3.2
USER root
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
USER airflow
RUN pip install --no-cache-dir deepface
RUN pip install --no-cache-dir pymongo