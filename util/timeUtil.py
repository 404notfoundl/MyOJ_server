import datetime

import pytz

from problem_lib import models

cid_keys = ["competition_id", "cid"]


def check_time(attrs, mode=''):
    """
    判断时间
    :param attrs:
    :param mode: 大于，小于或在范围内
    :return:
    """
    cid = None
    for key in cid_keys:
        cid = attrs.get(key, None)
        if cid is not None:
            break
    if cid is None:
        raise ValueError('未知的竞赛')
    competition = models.Competition.objects.filter(id=cid).first()
    if competition is None:
        raise ValueError('未知的竞赛')
    start = competition.startDate
    end = competition.endDate
    now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
    if start < now < end:
        pass
    else:
        if start > now:
            err = "还没开始"
            if mode != 'l':
                raise ValueError(err)
        else:
            err = "已经结束"
            if mode != 'g':
                raise ValueError(err)


def check_time_gt(left: datetime, right: datetime):
    """
    判断left>right
    :param left:
    :param right:
    :return:
    """
    return left > right


def check_time_lt(left: datetime, right: datetime):
    """
    判断left<right
    :param left:
    :param right:
    :return:
    """
    return left < right
