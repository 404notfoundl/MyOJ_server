from django.contrib.auth import get_user_model
from . import models
from rest_framework import serializers


class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = models.SiteConfig
