from django.db import models

contentSize = 20 * 1024  # 20K
labelSize = 1024  # 1K


class AbsProblems(models.Model):
    """
    存储题目的表
    """
    acceptNum = models.IntegerField(default=0, verbose_name='通过数')
    difficulty = models.CharField(max_length=6, verbose_name='难度')
    label = models.CharField(max_length=labelSize, verbose_name='标签')
    memoryLimit = models.IntegerField(default=128, verbose_name='空间限制')
    submitNum = models.IntegerField(default=0, verbose_name='提交数')
    title = models.CharField(max_length=20, verbose_name='标题')
    timeLimit = models.IntegerField(default=1000, verbose_name='时间限制')
    value = models.TextField(max_length=contentSize, verbose_name='内容')
    method = models.IntegerField(default=0, verbose_name="评测模式，0：通常 1:spj")

    class Meta:
        abstract = True

    def __str__(self):
        return self.title
