from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenVerifySerializer
from rest_framework import serializers
from jwt import decode as jwt_decode
from . import models
import re

User = get_user_model()


def set_user_name(name):
    """
    指定查询的键
    :param name: 名字
    :return: 无
    """
    User.USERNAME_FIELD = name


class LoginTokenSerializer(TokenObtainPairSerializer):
    # username_field = 'email'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['pid'] = user.id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['token'] = data['access']
        del data['access']
        data['uid'] = self.user.id
        data['isAdmin'] = self.user.is_superuser
        data['username'] = self.user.username
        data["avatarUrl"] = self.user.avatar_url
        return data


class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

    def validate_password(self, password):
        if not re.match(r"^[\w\W]{8,16}$", password):
            raise serializers.ValidationError('密码应由字母，数字，符号组成，且长度为8-16位。')
        return password


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'accept_num', 'submit_num', 'avatar_url']


class UserInfoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['avatar_url']


class UserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserInfo
        fields = "__all__"


class UserInfoIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserInfoIndex
        fields = '__all__'
