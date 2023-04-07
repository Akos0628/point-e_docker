# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /app

RUN apt-get update -yq \
    && apt-get install -yq \
    git

RUN git clone https://github.com/openai/point-e.git

WORKDIR /app/point-e

RUN pip install -e .
RUN pip install Flask

COPY app.py app.py

CMD ["python3", "app.py"]