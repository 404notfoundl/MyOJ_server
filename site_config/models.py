from django.db import models


# Create your models here.

class SiteConfig(models.Model):
    """
    相关的配置
    """
    key = models.CharField(verbose_name="键", primary_key=True, max_length=32)
    value = models.CharField(verbose_name="值", max_length=2048)
    backup = models.CharField(default="", max_length=2048)
    backup_2 = models.CharField(default="", max_length=2048)

    class Meta:
        db_table = "site_config"
