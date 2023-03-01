# Create your tasks here
from __future__ import absolute_import, unicode_literals

import time

from util import util
from online_judge.celery import app


@app.task
def test():
    time.sleep(3)
    print("test")
    return True


@app.task
def send_email(to, link) -> bool:
    return util.SiteEMail.send_link(to, link)

