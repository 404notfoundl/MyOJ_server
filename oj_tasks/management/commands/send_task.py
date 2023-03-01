import json
import uuid

from django.core.management import BaseCommand, CommandError
from util import pyRabbitMq


class Command(BaseCommand):
    help = '发送测试任务'

    def add_arguments(self, parser):
        parser.add_argument('-n', '--num', type=int, required=True, help='发送次数')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-t', '--task', type=str, help='任务的json格式字符串')
        group.add_argument('-f', '--file', type=str, help='从文件读取')

    def handle(self, *args, **options):
        if options['num'] <= 0:
            raise CommandError('num应当大于0')
        task_str = options.get('task', None)
        if task_str is None:
            file_src = options.get('file', None)
            with open(file_src, 'r') as fd:
                try:
                    task = json.load(fd)
                except json.decoder.JSONDecodeError:
                    raise CommandError('task格式错误')
        else:
            try:
                task = json.loads(task_str)
            except json.decoder.JSONDecodeError:
                raise CommandError('task格式错误')
        publisher = pyRabbitMq.RabbitMqPublisher()
        for i in range(0, options['num']):
            task['uuid'] = uuid.uuid4().hex
            publisher.basic_publish(json.dumps(task, ensure_ascii=False))
        publisher.connection.close()
        publisher.connection = None
