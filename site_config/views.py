import json

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework import mixins, status, permissions
from . import models, serializers
from util import util, permission as oj_permission, pyRedis


# Create your views here.
class SiteConfigView(ModelViewSet):
    serializer_class = serializers.SiteConfigSerializer
    queryset = models.SiteConfig.objects.all()
    permission_classes = [oj_permission.IsAdminOrReadOnly]

    def get_accessible(self, permission_level) -> dict:
        db_key = 'accessible'
        query_key = "site_accessible_{}".format(permission_level)
        rtn = pyRedis.get_cache(query_key)
        if rtn is None:
            rtn: dict = json.loads(self.get_queryset().filter(key=db_key).first().value)
            rtn = dict(filter(lambda i: i[1] <= permission_level, rtn.items()))
            pyRedis.set_cache(query_key, rtn)
        return rtn

    def list(self, request, *args, **kwargs):
        access = self.get_accessible(request.user.is_superuser)
        if not request.user.is_superuser:
            self.queryset = self.get_queryset().filter(key__in=access)
        return super().list(request, args, kwargs)

    def retrieve(self, request, *args, **kwargs):
        access = self.get_accessible(request.user.is_superuser)
        if kwargs['pk'] not in access and not request.user.is_superuser:
            return Response({"result": "不能访问或没有该项"})
        return super().retrieve(request, args, kwargs)

    def update(self, request, *args, **kwargs):
        res = super().update(request, args, kwargs)
        return res
