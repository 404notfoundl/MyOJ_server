# Create your views here.
import re
import uuid

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import status, mixins, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from . import serializers, models, tasks
from util import permission as oj_permission, util, pyRedis

User = get_user_model()
user_key = settings.REDIS_KEYS['user_key']  # redis 中缓存键名

LOCAL_HOST = settings.FRONT_END_HOST


def redirect_index(uid: int):
    return int(uid / models.user_size)


def get_table(uid: int, create: bool) -> models.UserInfo:
    """
    获取分表
    :param uid:用户编号
    :param create:是否创建新表
    :return:
    """
    if uid is not None:
        try:
            uid = int(uid)
        except ValueError as e:
            raise ValueError("未知的用户")
    else:
        raise ValueError("未知的用户")
    uid = redirect_index(uid)
    now_model = models.UserInfo.get_solution_db_model(uid=uid)
    cnt = models.UserInfoIndex.objects.filter(uid=uid).count()
    # 不存在创建一个库
    if not cnt and create:
        models.create_new_table(now_model)
        serial = serializers.UserInfoIndexSerializer(data={"uid": uid})
        if serial.is_valid():
            serial.save()
        else:
            raise ValueError("建立索引失败")
    elif not cnt:
        raise ValueError("不存在该库")
    return now_model


def get_data(start: int, size: int):
    problems = models.SiteUser.objects.all()
    serializer = serializers.UserInfoSerializer(problems, many=True)
    return serializer.data[start * size:(start + 1) * size]


class UserLoginView(TokenObtainPairView):
    """
    登录视图
    """
    serializer_class = serializers.LoginTokenSerializer

    def post(self, request, *args, **kwargs):

        is_email_mode = request.data.get('mode')
        if is_email_mode == 'email':
            serializers.set_user_name('email')
        elif is_email_mode != 'name':
            return Response({'result': '未知登陆模式'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = serializers.LoginTokenSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'result': '用户名或密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        data = Response(serializer.validated_data, status=status.HTTP_200_OK)

        if is_email_mode == 'email':
            serializers.set_user_name('username')
        return data


class UserRegister(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        serializer = serializers.UserAccountSerializer(data=request.data)
        if serializer.is_valid():
            pass
        else:
            return Response({'result': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.data
        new_uuid = uuid.uuid4().hex
        address = LOCAL_HOST + "/register/" + new_uuid
        tasks.send_email.delay(data.get("email", None), address)
        pyRedis.set_cache(new_uuid, data, util.SiteEMail.timeout)
        return Response({'result': '稍后将发送邮件，请注意查收'}, status=status.HTTP_200_OK)

    def put(self, request):
        pk = request.data.get('pk')
        msg = "已成功注册"
        state = status.HTTP_200_OK
        data = pyRedis.get_cache(pk)

        if data is None:
            msg = "注册信息已过期或者不存在，请重新注册"
        else:
            instance = models.SiteUser.objects.create_user(username=data['username'], password=data['password'],
                                                           email=data['email'])
            pyRedis.delete_key(pk)
            data['id'] = instance.id
            pyRedis.DataSlice.delete(user_key, pyRedis.DataSlice.slice(instance.id - 1))
        return Response({"result": msg}, status=state)


class UserView(GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    queryset = User.objects.all()
    serializer_class = serializers.UserInfoSerializer
    permission_classes = [IsAuthenticated]
    # 邮箱脱敏处理
    re_pattern = regexp = re.compile(r"^(\w{1,3})\w*(@\w+.\w+)$")

    @oj_permission.wrap_permission(oj_permission.IsUserSelf)
    def update(self, request, *args, **kwargs):
        self.serializer_class = serializers.UserInfoUpdateSerializer
        response = super(UserView, self).update(request, args, kwargs)
        pyRedis.DataSlice.delete(user_key, pyRedis.DataSlice.slice(request.user.id - 1))
        return response

    def retrieve(self, request, *args, **kwargs):
        if not kwargs.get('pk').isdigit() or int(kwargs.get('pk')) < 1:
            return Response({'result': '找不到该用户'}, status=status.HTTP_400_BAD_REQUEST)
        data = pyRedis.DataSlice.retrieve(user_key, int(kwargs.pop('pk')) - 1, get_data)
        if data is None:
            return Response({'result': '找不到该用户'}, status=status.HTTP_400_BAD_REQUEST)
        data['email'] = re.sub(self.re_pattern, r"\1****\2", data['email'])
        return Response(data)


class UserDetailsView(GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin):
    serializer_class = serializers.UserDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_data(self, request) -> dict:
        type_id = request.data.get("type", None)
        if type_id not in models.UserInfo.name_map:
            raise ValueError("不允许或不存在的值")
        else:
            uid = request.user.id
            value = request.data.get("value", None)
            if value is None:
                raise ValueError("没有值")
            else:
                # 对应的models有详细
                data = dict()
                data["name"] = models.UserInfo.name_map[type_id]
                data["name_type"] = type_id
                data["value"] = value
                data["value_type"] = models.UserInfo.type_map[type_id].value
                data["uid"] = uid
        return data

    def list(self, request, *args, **kwargs):
        uid = request.query_params.get("uid", None)
        type_id = request.query_params.get("type", 1)  # 默认通过的题目
        try:
            user_model = get_table(uid, False)
        except ValueError as e:
            return Response({"result": e.args})
        self.queryset = user_model.objects.filter(uid=uid, name_type=int(type_id)).order_by("name")
        self.serializer_class.Meta.model = user_model
        return super().list(request, args, kwargs)

    def create(self, request, *args, **kwargs):
        rtn_msg = "ok"
        uid = request.user.id
        type_id = request.data.get("type", None)
        try:
            user_model = get_table(uid, True)
            item = user_model.objects.filter(uid=uid, name_type=type_id).first()
            if item is not None and item.value != '':
                rtn_msg = "已存在"
            else:
                self.serializer_class.Meta.model = user_model
                data = self.get_data(request)
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
        except ValueError as e:
            rtn_msg = e.args
        return Response({"result": rtn_msg})

    def update(self, request, *args, **kwargs):
        rtn_msg = "ok"
        uid = request.user.id
        type_id = int(request.data.get("type", None))
        try:
            user_model = get_table(uid, False)
            self.serializer_class.Meta.model = user_model
            data = self.get_data(request)
            partial = kwargs.pop('partial', False)
            instance = user_model.objects.filter(uid=uid, name_type=type_id).first()
            if instance is None:
                rtn_msg = "未找到"
            else:
                serializer = self.get_serializer(instance, data=data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
        except ValueError as e:
            rtn_msg = '\n'.join(e.args)
        return Response({"result": rtn_msg})
