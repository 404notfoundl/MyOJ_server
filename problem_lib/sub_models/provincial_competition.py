from django.db import models
from . import abstract_models


class ProvincialCompetitionList(abstract_models.AbsProblems):
    """
    省赛题目列表，现不使用
    """
    pid = models.IntegerField(verbose_name="题目序号", default=0)
    province = models.CharField(max_length=10, verbose_name="省份(首字母缩写)")
    year = models.IntegerField(verbose_name="年份")
    status = models.IntegerField(default=0, verbose_name="状态")

    class Meta:
        db_table = "provincial_competition"
        verbose_name = "省赛题目表"
        ordering = ['province', '-year', 'pid']
