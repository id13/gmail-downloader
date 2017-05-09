from celery import Celery
app = Celery('app',broker='amqp://admin:mypass@rabbitmq:5672',backend='rpc://',include=['app.tasks'])

