from django.contrib.auth import get_user_model
from django.conf import settings

from util import pyRedis
from . import models
from rest_framework import serializers
from site_users.views import get_data

User = get_user_model()


class ProblemSolutionSerializers(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = models.ProblemSolution

    def validate_uid(self, uid):
        try:
            uid = int(uid)
        except Exception as exc:
            raise serializers.ValidationError("未知用户编号")
        if not User.objects.filter(id=uid).exists():
            raise serializers.ValidationError("未知用户编号")
        return uid

    def validate(self, data):
        uid = data.get("uid", None)
        pid = data.get("pid", None)
        obj_id = "%d_%d" % (pid, uid)
        data['id'] = obj_id
        return data

    def to_representation(self, instance):
        rtn = super(ProblemSolutionSerializers, self).to_representation(instance)
        rtn['username'] = pyRedis.DataSlice.retrieve(settings.REDIS_KEYS['user_key'], instance.uid - 1, get_data)[
            'username']
        return rtn


class ProblemIndexSerializers(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = models.SolutionIndex


class ProblemBufferSerializers(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = models.SolutionBuffer

    def to_representation(self, instance):
        rtn = super().to_representation(instance)
        rtn['username'] = pyRedis.DataSlice.retrieve(settings.REDIS_KEYS['user_key'], instance.uid - 1, get_data)[
            'username']
        return rtn
