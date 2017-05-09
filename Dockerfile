FROM python:3.5.1
COPY ./app /opt/app
WORKDIR /opt/app
RUN pip install -r requirements.txt
