import json
import re

from django.db.models import Max, Count
from django.utils.datastructures import MultiValueDictKeyError, MultiValueDict
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from django.db import transaction
from rest_framework import permissions, mixins, status
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.response import Response
from .. import serializers, models
from util import util, files as ojFiles, ojExceptions, pyRedis, permission as ojPermission, timeUtil


@method_decorator(gzip_page, name='dispatch')
class ProvincialCompetitionView(ModelViewSet):
    queryset = models.provincial_competition.ProvincialCompetitionList.objects.all()
    serializer_class = serializers.provincial_competition.ProvincialCompetitionSerializer
    permission_classes = [ojPermission.IsAdminOrReadOnly]
    params_list = ['province', 'year', 'pid']

    def validate_params(self, params: dict, total: bool = False):
        """
        按顺序存在
        :param total: 是否需要完全匹配
        :param params:
        :return:
        """
        res = False
        count = 0
        for key in self.params_list:
            if key in params:
                res = True
                count += 1
            else:
                break
        if not total:
            return res
        else:
            return count == len(self.params_list)

    def is_unique(self, data: dict):
        province = data.get("province")
        year = data.get("year")
        pid = data.get("pid")
        res = False
        query_res = self.get_queryset().filter(province=province, year=year, pid=pid).first()
        if query_res is not None:
            raise ValueError("该题目已存在")

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        # 获取省份列表
        if not self.validate_params(query_params):
            return Response(
                self.get_queryset().values('province').annotate(count=Count('province')))
        data = self.get_queryset()
        if 'province' in query_params:
            data = data.filter(province=query_params.get('province', None))
            if 'year' in query_params:
                data = data.filter(year=query_params.get('year', None))
                if 'pid' in query_params:
                    data = self.get_serializer(data.filter(pid=query_params.get('pid', None)), many=True)
                    if len(data.data) > 0:
                        data = data.data[0]
                    else:
                        return Response({"result": '找不到该题目'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    data = data.values('pid', 'title')
            else:
                data = data.values('year').annotate(count=Count('year'))
        return Response(data)

    def create(self, request, *args, **kwargs):
        r_data = request.data
        if not self.validate_params(r_data):
            return Response({"result": '非法的参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            self.is_unique(r_data)
        except ValueError as e:
            return Response({"result": ';'.join(e.args)}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, args, kwargs)

    def retrieve(self, request, *args, **kwargs):
        return Response("不允许此调用")

    def destroy(self, request, *args, **kwargs):
        return Response("不允许此调用")
