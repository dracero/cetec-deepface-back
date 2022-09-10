FROM apache/airflow:latest
USER airflow
RUN pip3 install --no-cache-dir --default-timeout=100000  deepface
RUN pip3 install --no-cache-dir pymongo

USER root
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

RUN mkdir -p /preload_imgs
COPY ./preload_imgs /preload_imgs

USER airflow
RUN python3 /preload_imgs/preload.py