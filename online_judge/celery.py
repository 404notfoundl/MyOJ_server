from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.result import AsyncResult
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_judge.settings')

app = Celery('online_judge')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('online_judge.celeryconfig')

# Load task modules from all registered Django app configs.
# 注册相应任务
# app.autodiscover_tasks(['site_users', 'oj_tasks'])
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


def get_result(res: AsyncResult):
    if res.successful():
        result = res.get()
        print(result)  # 打印任务结果
    elif res.failed():
        print('任务失败')
    elif res.status == 'PENDING':
        print('任务等待中被执行')
    elif res.status == 'RETRY':
        print('任务异常后正在重试')
    elif res.status == 'STARTED':
        print('任务已经开始被执行')
