
# syntax=docker/dockerfile:1
FROM python:3.8-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
RUN apt-get update && apt-get install -y gunicorn3 python3.8-dev python3-pip build-essential 
COPY requirements.txt /code/
RUN pip install -r requirements.txt && rm -rf /var/lib/apt/lists/*
COPY . /code/
RUN python3 manage.py collectstatic --no-input && python3 manage.py makemigrations --no-input && python3 manage.py migrate
ENTRYPOINT exec gunicorn --bind :8000 --workers 2 --threads 8 --timeout 0 futnetnepal.wsgi:application  
