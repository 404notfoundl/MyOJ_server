from django.apps import apps
from django.db import models
from django.contrib.auth.models import AbstractUser
from util.util import FieldsType

# Create your models here.
# 已一个用户200通过计算
user_size = int(5e3)


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


class SiteUser(AbstractUser):
    email = models.EmailField(blank=False, unique=True)

    accept_num = models.IntegerField(default=0)
    submit_num = models.IntegerField(default=0)
    avatar_url = models.URLField(max_length=1024, default="")

    class Meta(AbstractUser.Meta):
        db_table = 'site_user'


class UserInfo(models.Model):
    # 用户相关信息记录
    # 通过的题目标签
    name = models.CharField(max_length=100, verbose_name="名称")
    name_type = models.IntegerField(verbose_name="0:标签，1：AC题目，2：难度，3：用户主页自定义词云")
    value = models.CharField(max_length=1024, verbose_name="值")
    value_type = models.IntegerField(default=0, verbose_name="值类型,0：字符串，1：数字")
    uid = models.IntegerField(verbose_name="用户编号")
    type_map = {
        "0": FieldsType.T_STR,  # 标签，
        "1": FieldsType.T_INT,  # AC的题目，
        "2": FieldsType.T_INT,  # 难度计数
        "3": FieldsType.T_STR,  # 自定义词云
    }
    # 允许通过请求修改的
    name_map = {
        # "0": "label",  # 标签，
        # "1": "AC ID",  # AC的题目，
        # "2": "AC difficulty count",  # 难度计数
        "3": "user word cloud",  # 自定义词云
    }

    def get_value(self):
        match self.type_map[str(self.name_type)]:
            case 0:
                return self.value
            case 1:
                return int(self.value)

    @classmethod
    def get_solution_db_model(cls, uid):
        """
        获取分表model类
        :param uid: 分表名称 userinfo_<uid>
        :return: 分表model类
        """
        table_name = 'userinfo_%s' % uid
        try:
            table = apps.get_model('site_users', table_name)
            return table
        except LookupError as e:
            class Meta:
                db_table = table_name
                # abstract = False

            attrs = {
                '__module__': cls.__module__,
                'Meta': Meta,
            }
            return type(table_name, (cls,), attrs)

    class Meta:
        abstract = True


class UserInfoIndex(models.Model):
    uid = models.IntegerField(blank=False, verbose_name="用户")

    class Meta:
        db_table = "userinfo_index"
