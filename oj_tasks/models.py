from django.apps import apps
from django.db import models
import uuid

# 分表基准，按一题1000提交计算,1000题一张表
problems_size = int(1e3)


# Create your models here.

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


class SubmitTaskModel(models.Model):
    code = models.CharField(max_length=10240, default='')  # 代码限制10K
    details = models.CharField(max_length=3000, default='')  # 储存结果,应当以数组返回，与status一一对应
    id = models.UUIDField(primary_key=True, default=uuid.uuid1, editable=False, null=False)
    memory_usage = models.IntegerField(default=0)  # 保留用作以后用
    lang = models.CharField(max_length=10, default='c')
    pid = models.IntegerField(default=0)
    status = models.CharField(max_length=150, default='')
    submitDate = models.DateTimeField(auto_now_add=True)
    time_usage = models.IntegerField(default=0)  # 保留用作以后用
    uid = models.IntegerField(default=0)
    # method = models.IntegerField(default=0, verbose_name="评测模式，0：通常")

    # judged = models.BooleanField(default=False)  # 是否评测过

    @classmethod
    def get_task_db_model(cls, pid: str):
        """
        获取分表model类
        :param pid: 分表名称 task_<pid>
        :return: 分表model类
        """
        table_name = 'task_%s' % pid
        try:
            model = apps.get_model("oj_tasks", table_name)
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


class CompetitionTaskModel(models.Model):
    code = models.TextField(max_length=10240, default='')  # 代码限制10K
    details = models.TextField(max_length=3000, default='')  # 储存结果,应当以数组返回，与status一一对应
    id = models.UUIDField(primary_key=True, default=uuid.uuid1, editable=False, null=False)
    memory_usage = models.IntegerField(default=0)  # 保留用作以后用
    lang = models.CharField(max_length=10, default='c')
    pid = models.IntegerField(default=0)
    cid = models.IntegerField(default=0)
    status = models.CharField(max_length=150, default='')
    submitDate = models.DateTimeField(auto_now_add=True)
    time_usage = models.IntegerField(default=0)  # 保留用作以后用
    uid = models.IntegerField(default=0)

    @classmethod
    def get_task_db_model(cls, competition_id: str):
        """
        获取分表model类
        :param competition_id: 分表名称 competition_task_<id>
        :return: 分表model类
        """
        table_name = 'competition_task_%s' % competition_id
        try:
            model = apps.get_model("oj_tasks", table_name)
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


class TaskIndex(models.Model):
    str_id = models.CharField(max_length=30, blank=False, verbose_name="提交记录标识", unique=True, default="")

    class Meta:
        db_table = "task_index"
