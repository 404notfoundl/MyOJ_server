from django.db import models
from .sub_models import provincial_competition, abstract_models

# Create your models here.
contentSize = 20 * 1024  # 20K
labelSize = 1024  # 1K


class Problems(abstract_models.AbsProblems):
    """
    存储题目的表
    """
    pid = models.BigAutoField(primary_key=True)

    class Meta:
        db_table = 'problems'
        ordering = ['pid', ]

    def __str__(self):
        return self.title


class ProblemsLabel(models.Model):
    word = models.CharField(max_length=50, null=False, verbose_name="标签", unique=True)
    count = models.IntegerField(verbose_name="该标签数量", null=False)

    class Meta:
        db_table = 'problems_label'

    @classmethod
    def unique_labels(cls, labels_new: list[str], labels_old: list[str]) -> set:
        """
        获取重复的键
        :param labels_new:
        :param labels_old:
        :return: 重复的键
        """
        str_map = set()
        rtn_map = set()
        for label in labels_new:
            str_map.add(label)
        for label in labels_old:
            if label in str_map:
                rtn_map.add(label)
        return rtn_map

    @classmethod
    def modify_labels(cls, labels: list[str], repetitive: set, d: int):
        """
        修改标签
        :param repetitive: 重复的键
        :param labels: 标签数组，','为分割
        :param d: 改变量，+1或-1
        :return:
        """

        for label in labels:
            if label in repetitive:
                continue
            db_row = cls.objects.filter(word=label).first()
            if db_row is not None:
                cnt = db_row.count + d
                db_row.count = cnt
                db_row.save()
            else:
                cls.objects.create(word=label, count=d)


# 以下是竞赛相关表
class Competition(models.Model):
    """
    竞赛表，储存相关信息
    """
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=30)
    startDate = models.DateTimeField()
    endDate = models.DateTimeField()
    description = models.TextField(max_length=4096)
    submitter = models.CharField(max_length=150)
    submitter_id = models.IntegerField(verbose_name="提交者编号")
    problemCount = models.IntegerField(verbose_name="题目总数")
    timeDeltaLength = models.IntegerField(verbose_name="罚时时长(分钟)")
    isActive = models.BooleanField(default=True, verbose_name="删除标记为false")

    class Meta:
        # abstract = True
        db_table = "competition"
        verbose_name = "竞赛信息表"
        ordering = ['startDate']


class CompetitionProblems(abstract_models.AbsProblems):
    """
    竞赛题目表，储存比赛题目
    """
    competition_id = models.IntegerField(verbose_name="从属于的竞赛")
    id = models.CharField(max_length=30, verbose_name="标识，型如competition_id_pid", primary_key=True)
    pid = models.IntegerField(verbose_name="竞赛题目的编号，如1，2，3。。。")

    class Meta:
        db_table = "competition_problems"
        verbose_name = "竞赛题目表"
        ordering = ['pid']


class CompetitionRank(models.Model):
    """
    竞赛排行表
    """
    competition_id = models.IntegerField(verbose_name="竞赛id")
    submitter_id = models.IntegerField(verbose_name="提交者编号")
    id = models.CharField(max_length=30, verbose_name="标识，型如competition_id_submitter_id", primary_key=True)
    submitter = models.CharField(max_length=150, verbose_name="提交者名称")
    acTimeList = models.CharField(max_length=1024, default="", verbose_name="通过的题目列表，本次的题目通过时间")  # 以,分割
    timeDeltaList = models.CharField(max_length=1024, default="", verbose_name="罚时记录表")  # 以,分割
    totalTime = models.IntegerField(default=0, verbose_name="总用时(秒)")
    acCount = models.IntegerField(default=0, verbose_name="通过题目数")

    class Meta:
        db_table = "competition_rank"
        verbose_name = "竞赛排名表"
        ordering = ['-acCount', 'totalTime']  # 通过越多，罚时越少排名越高
        # abstract = True
