## Armar el Docker
### Descargamos el docker-compose
Guardamos el docker-compose.yaml que nos provee Apache Airflow:
```
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.3.2/docker-compose.yaml'
```

Apache Airflow usa Docker Compose para correr, por ser una aplicación multi-container:
- airflow-scheduler: Monitorea y corre las tareas y DAGs.
- airflow-webserver: Deja disponible al webserver en  http://localhost:8080.
- airflow-worker: Ejecuta las tareas dadas por el scheduler.
- airflow-init: El servicio de inicialización.
- postgres: La base de datos.
- redis: Reenvia mensajes del scheduler al worker.

### Armamos un Dockerfile
En el archivo anterior no se contempla a Deepface ni a Pymongo, dos dependencias que necesitamos para nuestro código. Por esta razón, vamos a agregar un archivo llamado Dockerfile para instalarlos:

Usamos una imagen base de Apache Airflow. Las siguientes instrucciones se ejecutarán sobre esta:
```
FROM apache/airflow:2.3.2
```
Usando el usuario 'airflow' (que es el usuario sin permisos root de esta imagen) instalamos Deepface y Pymongo: 
```
USER airflow
RUN pip install --no-cache-dir deepface
RUN pip install --no-cache-dir pymongo
```
Con el usuario 'root' para instalar 'ffmpeg libsm6 libxext6' para poder correr el código de '/preload_imgs/preload.py':
```
USER root
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
```
Continuando con el usuario 'root', copiamos la carpeta 'preload_imgs' al Docker:
```
RUN mkdir -p /preload_imgs
COPY ./preload_imgs /preload_imgs
```
Por último, usando el usuario 'airflow', ejecutamos el código de '/preload_imgs/preload.py':
```
USER airflow
RUN python3 /preload_imgs/preload.py
```
'preload.py' contiene un código muy pequeño que usa Deepface. De esta manera, cuando se construya el Docker, se van a descargar los modelos de esta biblioteca.

### Utilizamos nuestro Dockerfile
Luego, podemos seguir las instrucciones de la línea 44 del docker-compose.yaml descargado, que nos indica que:
1. Comentemos la siguiente línea, que indica que se utilizará la imagen base de Apache Airflow:
```
image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.3.2}
```
2. Descomentamos la siguiente linea, que se utilizará el Dockerfile que armamos arriba.
```
build: .
```

### Más info
Más información
- Sobre el uso de Apache Airflow con Dockers: https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html
- Sobre customización de Dockers con Apache Airflow: https://airflow.apache.org/docs/docker-stack/build.html

## Ejecutar el Docker
```
// Construimos la imagen Docker a partir de Dockerfile con Docker Compose v1
docker-compose build
// o con Docker Compose v2
docker compose build

// Ejecutamos el Docker
docker-compose up
// o con Docker Compose v2
dockercompose up
```

## Agregar variables
Para agregar variables de entorno, acceder a la UI de Apache Airflow, y desde el menú Admin -> Variables. Hay que agregar las siguientes:
- MONGO_URL
- EMAIL_USER
- EMAIL_PASSWORD

### Más info
https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html
