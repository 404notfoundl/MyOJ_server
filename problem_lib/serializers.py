import datetime

import pytz
from django.contrib.auth.models import User
from rest_framework import serializers

from util import timeUtil
from . import models
from oj_tasks.management.commands import result_consumer
from .sub_serializers import provincial_competition
import re


class AllProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Problems
        fields = '__all__'

    def validate_label(self, label):
        if not re.match(r"^[\u4e00-\u9fa5,a-zA-Z0-9 ]+$", label):
            raise serializers.ValidationError({'label': "标签只应包含汉字，字母和数字，并且以','为分割"})
        return label


class ProblemPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Problems
        fields = ('pid', 'title', 'acceptNum', 'submitNum')


class ProblemsLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ProblemsLabel
        fields = ['word', 'count']


# 以下为竞赛相关类和方法

class CompetitionSerializer(serializers.ModelSerializer):
    """
    比赛信息序列化
    """

    @classmethod
    def is_active(cls, data: dict):
        return not data.get("isActive")

    def validate_startDate(self, val: datetime) -> datetime:
        now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        if val < now:
            raise ValueError('时间不可小于当前时间')
        return val

    def validate_endDate(self, val: datetime):
        now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        if val < now:
            raise ValueError('时间不可小于当前时间')
        return val

    class Meta:
        model = models.Competition
        fields = '__all__'


class CompetitionProblemSerializer(serializers.ModelSerializer):
    """
    比赛题目序列化
    """

    class Meta:
        model = models.CompetitionProblems
        fields = '__all__'

    def validate(self, attrs):
        # check_time(attrs)
        cid = attrs.get("competition_id", None)
        pid = attrs.get("pid", None)
        if cid is None or pid is None:
            raise ValueError("不正确的参数")
        u_id = "%s_%s" % (cid, pid)
        attrs['id'] = u_id

        return attrs


class CompetitionRankSerializer(serializers.ModelSerializer):
    """
    比赛排名序列化
    """

    class Meta:
        model = models.CompetitionRank
        fields = '__all__'

    def validate(self, attrs):
        attrs['id'] = "%d_%d" % (attrs['competition_id'], attrs['submitter_id'])
        competition = result_consumer.Command.get_competition_msg(attrs['competition_id'])
        count = int(competition['problemCount'])
        start_date = datetime.datetime.strptime(competition['startDate'], "%Y-%m-%dT%H:%M:%S%z")
        if timeUtil.check_time_gt(datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai')), start_date):
            raise serializers.ValidationError({"result": "比赛已经开始或已经结束"})
        ac_time_list = list()
        time_delta_list = list()
        for cnt in range(0, count):
            ac_time_list.append("")
            time_delta_list.append("")
        attrs['acTimeList'] = '#'.join(ac_time_list)
        attrs['timeDeltaList'] = '#'.join(time_delta_list)
        return attrs
