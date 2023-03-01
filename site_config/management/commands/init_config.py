from django.core.management import BaseCommand
from site_config import models


class Command(BaseCommand):
    help = '初始化相关配置'

    def add_arguments(self, parser):
        parser.add_argument('announcement', help="公告(支持markdown)")

    def handle(self, *args, **options):
        value = [
            {
                'key': 'accessible',
                'value': "{\"announcement\": 0}"
            },
            {
                'key': 'announcement',
                'value': options['announcement']
            }
        ]
        for val in value:
            model = models.SiteConfig.objects.filter(key=val['key'])
            if model is not None:
                model.update(**val)
                self.stdout.write('key %s updated' % val['key'])
            else:
                models.SiteConfig.objects.create(**val)
                self.stdout.write("key %s created" % val['key'])
