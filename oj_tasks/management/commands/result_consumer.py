import datetime
import json
import os

import pika.exceptions
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.conf import settings
from pytz import timezone
from retry import retry

from util import pyRabbitMq, pyRedis
from oj_tasks import views as task_views
from problem_lib import models as prob_models, serializers as prob_serializer
from site_users import models as user_models, views as user_views, serializers as user_serializers

User = get_user_model()

serializers = {
    "user": user_serializers
}

if not settings.DEBUG:
    res_que = "queue_result"
else:
    res_que = "test_queue_result"


def time_format(seconds: int):
    format_list = []
    total = seconds
    num = 0
    for cnt in range(0, 2):
        num = divmod(total, 60)
        format_list.append(int(num[1]))
        total = num[0]
    format_list.append(int(num[0]))
    return "%02d:%02d:%02d" % (format_list[2], format_list[1], format_list[0])


class Command(BaseCommand):
    # 帮助文本, 一般备注命令的用途及如何使用。
    help = "接收结果的客户端"

    @classmethod
    def get_competition_msg(cls, cid: int):
        """
        获取redis中存储的比赛信息
        :param cid:
        :return:
        """
        competition: dict = pyRedis.get_cache("competition_%d" % cid)
        if competition is None:
            competition = prob_serializer.CompetitionSerializer(
                prob_models.Competition.objects.filter(id=cid).first()).data
            pyRedis.set_cache("competition_details_%d" % cid, competition, 10800)
        return competition

    @classmethod
    def handle_competition_msg(cls, data, accepted: bool):
        """
        记录比赛中相关罚时信息
        :param accepted:
        :param data:
        :return:
        """
        cid = int(data['cid'])
        uid = int(data['uid'])
        pid = int(data['pid'])
        competition = cls.get_competition_msg(cid)
        rank_id = "%d_%d" % (cid, uid)
        competition_rank = prob_models.CompetitionRank.objects.filter(id=rank_id).first()
        ac_time_list = competition_rank.acTimeList.split('#')
        time_delta_list = competition_rank.timeDeltaList.split('#')
        # 仅在未通过时记录
        if ac_time_list[pid] == "":
            # AC记第一次通过时间
            time_delta = datetime.timedelta()
            if accepted:
                time_delta = data['submitDate'] - datetime.datetime.strptime(
                    competition.get("startDate"), "%Y-%m-%dT%H:%M:%S%z")
                ac_time_list[pid] = time_format(time_delta.total_seconds())
                competition_rank.acCount += 1
                print(str(data['submitDate']), str(datetime.datetime.strptime(
                    competition.get("startDate"), "%Y-%m-%dT%H:%M:%S%z")), str(time_delta))
            # 未AC记罚时
            else:
                td = time_delta_list[pid]
                if td == "":
                    td = 0
                else:
                    td = int(td)
                time_delta_list[pid] = str(td + 1)
                time_delta += datetime.timedelta(minutes=int(competition.get("timeDeltaLength")))
            competition_rank.totalTime += int(time_delta.total_seconds())
            # print(str(time_delta))
            competition_rank.acTimeList = '#'.join(ac_time_list)
            competition_rank.timeDeltaList = '#'.join(time_delta_list)
            competition_rank.save()

    @classmethod
    def handle_spj_checker(cls, res, accepted: bool):
        res['result'] = 0  # 已执行完成任务
        res['accept'] = int(not accepted)  # 是否通过
        res['has_set'] = False
        pyRedis.set_cache("%s_%s" % (settings.SPJ_KEY['prefix'], res['uuid']), res, 43200)

    @classmethod
    def handle_common_task(cls):
        pass

    # TODO 待重构，写的不好
    def callback(self, ch, method, properties, body: bytes):
        res = json.loads(body)
        if res.get('details', None) is not None and res.get('details', None) != '':
            res['details'] = '#'.join(res['details'])
            pid = res['pid']
            cid = res.get("cid", None)
            task_compile: bool = res.get("compile", False)
            task_runner: bool = res.get("runner", False)
            # 编辑器
            if pid == 0:
                pyRedis.set_cache(res['uuid'], res['details'], 600)
                ch.basic_ack(method.delivery_tag)
                return
            # spj 验证部分
            elif pid < 0:
                self.handle_spj_checker(res, task_compile & task_runner)
                ch.basic_ack(method.delivery_tag)
                return
            task_model = task_views.get_table(False, pid=pid, cid=cid)
            task = task_model.objects.filter(id=res['uuid']).first()
            # 评测结果

            # 比赛时的处理方法，除本身信息外需记录罚时信息，注意该表相关信息需要对齐
            if cid is not None:
                date = task.submitDate
                # 上海 +08:06
                res['submitDate'] = datetime.datetime(tzinfo=timezone("Asia/Shanghai"), year=date.year,
                                                      month=date.month, day=date.day, hour=date.hour + 8,
                                                      minute=date.minute + 6, second=date.second)
                self.handle_competition_msg(res, task_compile and task_runner)
                prob = prob_models.CompetitionProblems.objects.filter(pid=pid, competition_id=cid).first()
                prob.submitNum += 1
                if task_compile and task_runner:
                    prob.acceptNum += 1
                prob.save()
            else:
                if pid > 0:
                    # 对应题目提交数自增
                    prob = prob_models.Problems.objects.filter(pid=pid).first()
                    prob.submitNum += 1
                    user = User.objects.filter(id=res['uid']).first()
                    user_info_model = user_views.get_table(res['uid'], True)
                    user_info_ac = user_info_model.objects.filter(uid=res['uid'], name=pid).first()
                    # 通过
                    if task_compile and task_runner:
                        prob.acceptNum += 1
                        # 记录AC编号和标签
                        user_info_data = {
                            "uid": res['uid'],
                            "name": "",
                            "value": "",
                            "name_type": 1,
                            "value_type": 1
                        }
                        if user_info_ac is None:
                            # 未通过的题目计通过数
                            user.accept_num += 1
                            user.submit_num += 1
                            user_info_data['name'] = pid
                            user_info_data['value'] = 1
                            serial = user_serializers.UserDetailsSerializer(data=user_info_data)
                            serial.Meta.model = user_info_model
                            if serial.is_valid():
                                serial.save()
                            else:
                                self.log("data invalid")
                                return
                    else:
                        # 记录未通过，题目未通过计数增加
                        if user_info_ac is None:
                            user.submit_num += 1
                    pyRedis.delete_key(res["uid"])
                    prob.save()
                    user.save()
                    # 存入相关信息
                    if task is not None:
                        task.details = res['details']
                        task.status = res['status']
                        if 'time_usage' in res:
                            task.time_usage = res['time_usage']
                        if 'memory_usage' in res:
                            task.memory_usage = res['memory_usage']
                        task.save()
            self.log(
                'uid %d, pid %d complete, ac state %s' % (res['uid'], res['pid'], str(task_compile and task_runner)))
            ch.basic_ack(method.delivery_tag)
        else:
            self.log("unknown msg!")

        return

    # 核心业务逻辑
    @retry(pika.exceptions.AMQPConnectionError, tries=10, delay=60, backoff=2, max_delay=600)
    def handle(self, *args, **options):
        if settings.IS_LINUX:
            os.system("echo %d > consumer.pid" % os.getpid())
        self.log('pid: %d,当前的接收队列:%s 开始接收结果，ctrl c退出' % (os.getpid(), res_que))
        consume = pyRabbitMq.RabbitMqConsumer(queue_name=res_que)
        consume.basic_consume(callback=self.callback)
        consume.start_consuming()

    def log(self, msg: str):
        log_msg = '[{}] {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
        self.stdout.write(log_msg)
