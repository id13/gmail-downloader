FROM python:3.5.1
COPY ./app /app/
WORKDIR /app
RUN pip install -r requirements.txt
