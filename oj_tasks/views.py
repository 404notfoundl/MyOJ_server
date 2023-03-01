import json
import uuid

from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework import mixins, status, permissions
from . import serializers, models, tasks
from util import pyRabbitMq, pyRedis, permission, ojPagination, timeUtil
from problem_lib import models as problem_models


# Create your views here.

def get_table(create: bool, **params: int) -> models.SubmitTaskModel:
    if params is not None:
        try:
            task_id = int(params.get("pid"))
            cid = params.get("cid", None)
        except ValueError as e:
            raise ValueError("未知的题目")

    else:
        raise ValueError("未知的题目")
    if cid is not None:
        task_id = int(cid)
    task_id = redirect_index(task_id)
    # 比赛记录表
    if cid is not None:
        task_id: str = "c%d" % task_id
        now_model = models.CompetitionTaskModel.get_task_db_model(task_id)
    # 平时题目表
    else:
        task_id: str = "p%d" % task_id
        now_model = models.SubmitTaskModel.get_task_db_model(task_id)
    cnt = models.TaskIndex.objects.filter(str_id=task_id)
    # 不存在创建一个库
    if not cnt and create:
        models.create_new_table(now_model)
        serializer = serializers.TaskIndexSerializer(data={"str_id": task_id})
        if serializer.is_valid():
            serializer.save()
        else:
            raise ValueError("建立索引失败")
    elif not cnt:
        raise ValueError("不存在该库")
    return now_model


def send_task(data: dict):
    """
    发送消息至rabbitMq
    :param data: 数据
    :return: 无
    """
    task = json.dumps(data, ensure_ascii=False)
    connection = pyRabbitMq.RabbitMqPublisher()
    # print(task)
    connection.basic_publish(task)
    connection.connection.close()
    connection.connection = None


def redirect_index(obj_id: int):
    return int(obj_id / models.problems_size)


def serial(data, serializer):
    """
    序列化相关数据
    :param data: 待序列化数据
    :param serializer: 序列化的类
    :return:
    """
    cid = data.get('cid', None)
    data['uid'] = int(data['uid'])
    data['pid'] = int(data['pid'])
    # data['O2'] = bool(data.get("O2", False))
    data['O2'] = True
    data['uuid'] = str(serializer.instance.id).replace('-', '')
    if cid is not None:
        cid = int(cid)
        data['cid'] = cid
        prob_obj = problem_models.CompetitionProblems.objects.filter(id="%s_%s" % (cid, data['pid'])).first()
    else:
        prob_obj = problem_models.Problems.objects.filter(pid=data['pid']).first()
    data['time_limit'] = prob_obj.timeLimit
    data['mem_limit'] = prob_obj.memoryLimit
    data['method'] = prob_obj.method


@method_decorator(gzip_page, name='dispatch')
class PreJudgeView(GenericViewSet, mixins.CreateModelMixin):
    """
    提交任务给评测
    """
    serializer_class = serializers.CreateTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        uid = request.user.id
        pid = int(request.data.get("pid", None))
        if uid is None:
            return Response({'result': '未知用户'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        if pid <= 0:
            if pid == 0:  # 编辑器提交
                data['time_limit'] = 1000
                data['mem_limit'] = 128
                data['uuid'] = uuid.uuid4().hex
                data['uid'] = uid
                data['pid'] = pid
                data['O2'] = False
                data['method'] = 0
                tasks.send_task.delay(data)
                return Response({'result': "提交成功", 'uuid': data['uuid']}, status=status.HTTP_201_CREATED)
            else:
                return Response({'result': '未知的题目'}, status=status.HTTP_404_NOT_FOUND)
        else:
            data['uid'] = uid
            try:
                serializers.CreateTaskSerializer.validate_request(data)
                now_model = get_table(True, pid=pid)
                self.queryset = now_model.objects.all()
                self.serializer_class.Meta.model = now_model
                serializer = self.get_serializer(data=data)
                serializer.is_valid()
                self.perform_create(serializer)
            except ValueError as e:
                return Response({'result': e.args}, status=status.HTTP_400_BAD_REQUEST)
        serial(data, serializer)
        tasks.send_task.delay(data)
        return Response({'result': '提交成功'}, status=status.HTTP_201_CREATED)


@method_decorator(gzip_page, name='dispatch')
class AfterJudgeView(GenericViewSet, mixins.UpdateModelMixin, mixins.ListModelMixin):
    """
    评测后结果处理，现不使用，改用result_consumer
    """
    serializer_class = serializers.SubmitTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ojPagination.TaskPagination

    @permission.wrap_permission(permissions.IsAdminUser)
    def update(self, request, *args, **kwargs):
        try:
            serializers.SubmitTaskSerializer.validate_request(request.data)
            now_model = get_table(False, pid=request.data.get("pid"))
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_404_NOT_FOUND)
        self.queryset = now_model.objects.all()
        self.serializer_class.Meta.model = now_model
        self.lookup_field = 'id'
        self.kwargs['id'] = request.data.get('id')
        return super().update(request, args, kwargs)

    def list(self, request, *args, **kwargs):
        pid = int(request.query_params.get("pid"))
        if pid == 0:
            q_uuid = request.query_params.get("uuid")
            output = pyRedis.get_cache(q_uuid)
            if output is None:
                return Response({"result": "已失效或不存在", "code": 0})
            pyRedis.delete_key(q_uuid)
            return Response({"result": output, "code": 1})
        try:
            now_model = get_table(False, pid=pid)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_404_NOT_FOUND)
        self.queryset = now_model.objects.filter(uid=request.query_params.get('uid'),
                                                 pid=pid)
        self.serializer_class.Meta.model = now_model
        return super().list(request, args, kwargs)


class CompetitionJudgeView(GenericViewSet, mixins.CreateModelMixin, mixins.ListModelMixin):
    serializer_class = serializers.CompetitionTaskSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = ojPagination.TaskPagination
    throttle_classes = (UserRateThrottle,)

    def create(self, request, *args, **kwargs):
        try:
            uid = request.user.id
            cid = int(request.data.get("cid", None))
            pid = int(request.data.get("pid", None))
            timeUtil.check_time(request.data)
            if problem_models.CompetitionRank.objects.filter(id="%s_%s" % (cid, uid)).first() is None:
                return Response({"result": "请先报名"})
        except Exception as e:
            return Response({"result": e.args})
        try:
            data = request.data.copy()
            data['uid'] = uid
            serializers.CompetitionTaskSerializer.validate_request(data)
            now_model = get_table(True, pid=pid, cid=cid)
        except Exception as e:
            return Response({"result": e.args}, status=status.HTTP_404_NOT_FOUND)
        self.queryset = now_model.objects.all()
        self.serializer_class.Meta.model = now_model
        serializer = self.get_serializer(data=data)
        serializer.is_valid()
        # return Response({"result": "已提交"})

        self.perform_create(serializer)
        serial(data, serializer)
        tasks.send_task.delay(data)
        return Response({"result": "已提交"})

    def list(self, request, *args, **kwargs):
        try:
            uid = request.user.id
            cid = int(request.query_params.get("cid", None))
            pid = int(request.query_params.get("pid", None))
            now_model = get_table(False, pid=pid, cid=cid)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_404_NOT_FOUND)
        self.queryset = now_model.objects.filter(uid=uid, pid=pid, cid=cid)
        self.serializer_class = serializers.CompetitionTaskViewSerializer
        self.serializer_class.Meta.model = now_model
        return super().list(request, args, kwargs)
