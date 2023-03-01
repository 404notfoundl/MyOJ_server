from django.contrib.auth import get_user_model
from rest_framework import serializers
from . import models
from problem_lib import models as problem_model

User = get_user_model()


def validator_null(fields, request):
    result = list()
    f = None
    valid = True
    for field in fields:
        f = request.get(field, None)
        if f is None:
            valid = False
            result.append("%s 不能为空" % field)
    if not valid:
        raise serializers.ValidationError(result)


class SubmitTaskSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = models.SubmitTaskModel

    @classmethod
    def validate_request(cls, data):
        fields = ['id', 'status', "details", 'pid']
        validator_null(fields, data)


class CreateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubmitTaskModel
        # TODO 检测是否支持该语言
        fields = ['code', 'lang', 'uid', 'pid']

    @classmethod
    def validate_request(cls, data):
        fields = cls.Meta.fields
        validator_null(fields, data)

    @classmethod
    def validate_uid(cls, uid):
        try:
            uid = int(uid)
        except Exception as exc:
            raise serializers.ValidationError("未知用户编号")
        if not User.objects.filter(id=uid).exists():
            raise serializers.ValidationError("未知用户编号")
        return uid

    @classmethod
    def validate_pid(cls, pid):
        try:
            pid = int(pid)
        except Exception as exc:
            raise serializers.ValidationError("未知的题目编号")
        if not problem_model.Problems.objects.filter(pid=pid).exists():
            raise serializers.ValidationError("未知的题目编号")
        return pid


class CompetitionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CompetitionTaskModel
        fields = ['code', 'lang', 'uid', 'pid', 'cid']

    @classmethod
    def validate_request(cls, data):
        fields = cls.Meta.fields
        validator_null(fields, data)

    @classmethod
    def validate_uid(cls, uid):
        try:
            uid = int(uid)
        except Exception as exc:
            raise serializers.ValidationError("未知用户编号")
        if not User.objects.filter(id=uid).exists():
            raise serializers.ValidationError("未知用户编号")
        return uid


class CompetitionTaskViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CompetitionTaskModel
        fields = "__all__"


class TaskIndexSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = models.TaskIndex
