FROM python:3.6

MAINTAINER Yadav  Lamichhane < omegazyadav1@gmail.com>

ENV PYTHONUNBUFFERED 1

RUN mkdir /code

WORKDIR /code

COPY requirements.txt /code/

RUN pip install -r requirements.txt

COPY . /code/

