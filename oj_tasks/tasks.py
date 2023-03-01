# Create your tasks here
from __future__ import absolute_import, unicode_literals

import json

from util import util, pyRabbitMq
from online_judge.celery import app


@app.task
def send_task(data: dict) -> int:
    task = json.dumps(data, ensure_ascii=False)
    connection = pyRabbitMq.RabbitMqPublisher()
    # print(json.dumps(data))
    connection.basic_publish(task)
    connection.connection.close()
    connection.connection = None
    return -1


@app.task
def test():
    print('test tasks')
