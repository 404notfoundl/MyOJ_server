from django.apps import apps
from django.db import models

# 一张表所放题目数量，按一题50题解计算
problem_size = int(1e4)


def create_new_table(model):
    """
    创建新表
    :param model:model类
    :return: 无
    """
    from django.db import connection
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor
    with BaseDatabaseSchemaEditor(connection) as editor:
        editor.create_model(model=model)


class ProblemsPublic(models.Model):
    uid = models.IntegerField(verbose_name="用户编号")
    pid = models.IntegerField(verbose_name="题目编号")
    username = models.CharField(verbose_name="用户名", max_length=30)
    value = models.TextField(max_length=20480)
    submitDate = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Create your models here.
class ProblemSolution(ProblemsPublic):
    # 用户与题解为一对一
    id = models.CharField(max_length=30, primary_key=True, verbose_name="主键，pid_uid")

    @classmethod
    def get_solution_db_model(cls, pid):
        """
        获取分表model类
        :param pid: 分表名称 solution_P<pid>
        :return: 分表model类
        """
        table_name = 'solution_%s' % pid
        try:
            model = apps.get_model("solutions", table_name)
            return model
        except LookupError as e:
            class Meta:
                db_table = table_name
                ordering = ("-submitDate",)

            attrs = {
                '__module__': cls.__module__,
                'Meta': Meta,
            }
            return type(table_name, (cls,), attrs)

    class Meta:
        abstract = True


class SolutionBuffer(ProblemsPublic):
    """
    做题解审核
    """
    status = models.IntegerField(default=1, verbose_name="审核状态，0：通过，1：待审核，2：未通过")

    # remark = models.TextField(default="")

    class Meta:
        db_table = "solution_buffer"
        ordering = ("-submitDate",)


class SolutionIndex(models.Model):
    """
    索引题解,辅助判断对应的表是否出现
    """
    pid = models.IntegerField(blank=False, verbose_name="题解编号")

    class Meta:
        db_table = 'solution_index'
