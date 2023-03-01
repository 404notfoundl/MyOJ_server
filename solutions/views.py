from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.datastructures import MultiValueDictKeyError
from django.views.decorators.gzip import gzip_page
from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework import mixins, status, permissions
from . import models, serializers
from util import util, permission as ojPermission


# Create your views here.

def get_cache(key: str):
    data = cache.get(key)
    return data


def set_cache(key: str, value, time=60):
    cache.set(key, value, timeout=time)


def get_solution_buffer():
    solution_buffer = get_cache("solution_buffer")
    total_solutions = get_cache("total_solutions")
    if solution_buffer is None:
        solution_buffer = models.SolutionBuffer.objects.all()
        serializer = serializers.ProblemBufferSerializers(solution_buffer, many=True)
        set_cache('solution_buffer', serializer.data, 30 * 60)
        solution_buffer = serializer.data
    if total_solutions is None:
        total_solutions = models.SolutionBuffer.objects.count()
        set_cache('total_solutions', total_solutions, 30 * 60)
    return solution_buffer, total_solutions


def get_table(pid: int, create: bool) -> models.ProblemSolution:
    """
    获取分表
    :param pid:题目编号
    :param create:是否创建新表
    :return:
    """
    if pid is not None:
        try:
            pid = int(pid)
        except ValueError as e:
            raise ValueError("未知的题目")
    else:
        raise ValueError("未知的题目")
    pid = redirect_index(pid)
    now_model = models.ProblemSolution.get_solution_db_model(pid=pid)
    cnt = models.SolutionIndex.objects.filter(pid=pid).count()
    # 不存在创建一个库
    if not cnt and create:
        models.create_new_table(now_model)
        serial = serializers.ProblemIndexSerializers(data={"pid": pid})
        if serial.is_valid():
            serial.save()
        else:
            raise ValueError("建立索引失败")
    elif not cnt:
        raise ValueError("不存在该库")
    return now_model


def redirect_index(pid: int) -> int:
    return int(pid / models.problem_size)


class ProblemSolutionView(ModelViewSet):
    """
    分表的增改
    """
    # queryset = models.ProblemSolution.objects.all()
    serializer_class = serializers.ProblemSolutionSerializers
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        try:
            now_model = get_table(int(request.data.get('pid')), True)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_200_OK)
        self.queryset = now_model.objects.all()
        self.serializer_class.Meta.model = now_model
        return super().create(request, args, kwargs)

    def update(self, request, *args, **kwargs):
        try:
            now_model = get_table(int(request.data.get('pid')), False)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_200_OK)
        self.queryset = now_model.objects.all()
        self.serializer_class.Meta.model = now_model
        self.lookup_field = 'uid'
        self.kwargs['uid'] = int(request.data.get('uid'))
        return super().update(request, args, kwargs)

    def list(self, request, *args, **kwargs):
        return Response({"result": "不允许此调用"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def retrieve(self, request, *args, **kwargs):
        return Response({"result": "不允许此调用"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"result": "不允许此调用"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@method_decorator(gzip_page, name='dispatch')
class PreviewProblemSolutionView(GenericViewSet, mixins.ListModelMixin):
    """
    分表的查询
    """
    serializer_class = serializers.ProblemSolutionSerializers

    def list(self, request, *args, **kwargs):
        try:
            now_model = get_table(int(request.query_params.get('pid')), False)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_200_OK)
        except TypeError as e:
            return Response({"result": "未知的pid"}, status=status.HTTP_200_OK)

        self.queryset = now_model.objects.filter(pid=request.query_params.get('pid'))
        self.serializer_class.Meta.model = now_model
        return super().list(request, args, kwargs)


@method_decorator(gzip_page, name='dispatch')
class SolutionBufferView(ModelViewSet):
    """
    审核题解
    """
    serializer_class = serializers.ProblemBufferSerializers
    queryset = models.SolutionBuffer.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        temp = models.SolutionBuffer.objects.filter(pid=request.data.get("pid"), uid=request.data.get("uid"))
        if temp.__len__() > 0:
            return Response({"result": "已提交过该题题解"}, status=status.HTTP_200_OK)
        try:
            now_model = get_table(int(request.data.get('pid')), True)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_200_OK)
        temp = now_model.objects.filter(pid=request.data.get("pid"), uid=request.data.get("uid"))
        if temp.exists():
            return Response({"result": "已提交过该题题解"}, status=status.HTTP_200_OK)

        # TODO 待修改，效率不高
        cache.delete_pattern('solution_buffer')
        cache.delete_pattern('total_solutions')
        super().create(request, args, kwargs)
        return Response({"result": "提交成功,请等待审核"}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        self.queryset = models.SolutionBuffer.objects.filter(pid=request.data.get("pid"))
        self.lookup_field = 'uid'
        self.kwargs['uid'] = request.data.get("uid")
        buffer_instance = self.get_object()
        serializer = serializers.ProblemBufferSerializers(instance=buffer_instance, data=request.data)
        try:
            if not serializer.is_valid():
                return Response({"result": serializer.errors}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"result": e.args}, status=status.HTTP_200_OK)
        serializer.save()
        # TODO 待修改，效率不高
        cache.delete_pattern('solution_buffer')
        cache.delete_pattern('total_solutions')
        return Response({"result": "修改成功"})  # super().update(request, args, kwargs)

    def retrieve(self, request, *args, **kwargs):
        self.queryset = models.SolutionBuffer.objects.filter(pid=request.query_params.get("pid"))
        self.lookup_field = 'uid'
        self.kwargs['uid'] = request.query_params.get("uid")
        try:
            buffer_instance = self.get_object()
        except Http404:
            return Response({"result": 404})

        serializer = self.get_serializer(instance=buffer_instance)
        return Response(serializer.data)

    @ojPermission.wrap_permission(permissions.IsAdminUser)
    def destroy(self, request, *args, **kwargs):
        keys = kwargs.get("pk").split("&")  # 0:uid 1:pid
        self.queryset = self.get_queryset().filter(pid=keys[1])
        self.lookup_field = 'uid'
        self.kwargs['uid'] = keys[0]
        buffer_instance = self.get_object()
        super().perform_destroy(buffer_instance)
        # TODO 待修改，效率不高
        cache.delete_pattern('solution_buffer')
        cache.delete_pattern('total_solutions')
        return Response(status=status.HTTP_200_OK)

    @ojPermission.wrap_permission(permissions.IsAdminUser)
    def list(self, request, *args, **kwargs):
        (solution_buffer, total_solutions) = get_solution_buffer()
        try:
            value = util.slice_data2(request, solution_buffer)
        except MultiValueDictKeyError as e:
            return Response({'result': e.args}, status=status.HTTP_200_OK)
        total = {'total': total_solutions}
        value.insert(0, total)
        return Response(value)
