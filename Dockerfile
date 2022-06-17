FROM apache/airflow:2.3.2
USER airflow
RUN pip install --no-cache-dir deepface
RUN pip install --no-cache-dir pymongo

USER root
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

RUN mkdir -p /preload_imgs
COPY ./preload_imgs /preload_imgs
COPY ./preload_imgs/img /preload_imgs/img

USER airflow
RUN python3 /preload_imgs/preload.py
