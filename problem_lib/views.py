import datetime
import json
import os
import re
import uuid
from distutils.util import strtobool

from celery.result import AsyncResult
from django.db.models import Max
from django.utils.datastructures import MultiValueDictKeyError, MultiValueDict
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from rest_framework import permissions, mixins, status
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.response import Response
from . import serializers, models, tasks
from util import util, files as ojFiles, ojExceptions, pyRedis, permission as ojPermission, timeUtil
from django.conf import settings
from .sub_views import provincial_competition
from oj_tasks import tasks as oj_task

# Create your views here.

problem_key = settings.REDIS_KEYS['problem_key']
keys = {
    'problem': "problems",
    'competition': 'competition'
}


# TODO 整理备份文件的相关函数

def validate_test_case(prob_files: MultiValueDict, ):
    """
    文件格式校验
    :param prob_files:
    :return:
    """
    input_files = prob_files.getlist('input')
    output_files = prob_files.getlist('output')

    input_pattern = re.compile("(.in)$")
    output_pattern = re.compile("(.out)$")
    name_set = set()
    error = list()
    if len(input_files) != len(output_files):
        raise ojExceptions.FileInvalidError("输入文件与输出文件数量不匹配")

    for cnt in range(0, len(input_files)):
        if not input_pattern.search(input_files[cnt].name):
            raise ojExceptions.FileInvalidError("输入文件后缀不正确:%s" % input_files[cnt].name)
        in_name = util.split_str(input_files[cnt].name, '.')
        name_set.add(in_name)

    for cnt in range(0, len(output_files)):
        if not output_pattern.search(output_files[cnt].name):
            raise ojExceptions.FileInvalidError("答案文件后缀不正确:%s" % output_files[cnt].name)
        out_name = util.split_str(output_files[cnt].name, '.')
        if out_name not in name_set:
            error.append(out_name)
    if len(error) > 0:
        raise ojExceptions.FileInvalidError("存在未匹配文件，如下：%s" % ','.join(error))


# 存放比赛测试点的路径 (C)cid/(P)pid/(P)pid_%d
def backup_problems(prob_files: MultiValueDict, pid: int, cid: int = None):
    """
    预计备份题目，可使用rsync与评测机之间同步数据
    :param prob_files:
    :param cid:
    :param pid:
    :return:
    """
    list_length = len(prob_files.getlist('input'))
    if list_length == 0:
        return
    validate_test_case(prob_files)
    if cid is not None:
        dir_name = "C%d/P%d" % (cid, pid)
    else:
        dir_name = "P%d" % pid
    list_len_path = "%s/%s" % (settings.MEDIA_ROOT, dir_name)
    dir_name = "%s/%s" % (settings.MEDIA_ROOT, dir_name)
    ojFiles.write_list_length(list_length, list_len_path)
    input_pattern = re.compile("(.in)$")
    output_pattern = re.compile("(.out)$")
    for file_list in prob_files:
        count = 0
        for file in prob_files.getlist(file_list):
            if input_pattern.search(file.name):
                format_file_name(file, count, '')
            elif output_pattern.search(file.name):
                format_file_name(file, count, '.out')

            count += 1
            # name = "%s/P%d_%s" % (dir_name, pid, file.name)
            name = "P%d_%s" % (pid, file.name)
            # os.makedirs(dir_name, 0o777, exist_ok=True)
            # os.chmod(dir_name, 0o777)
            # ojFiles.save_to_local(name, file)
            ojFiles.save_bin(dir_name, name, file.file)


def spj_backup(prob_files: list, pattern_path: str, suffix: str, pid: str):
    count = 0
    for file in prob_files:
        format_file_name(file, count, suffix)
        file.name = "%s_%s" % (pid, file.name)
        count += 1
        ojFiles.save_bin(pattern_path, file.name, file.file)


def format_file_name(file, count: int, end: str):
    file.name = "%d%s" % (count, end)


def get_data(start: int, size: int):
    problems = models.Problems.objects.all()
    serializer = serializers.AllProblemSerializer(problems, many=True)
    return serializer.data[start * size:(start + 1) * size]


def add_spj_problem_list(pid: int):
    # 添加全局spj题目标识
    all_spj_files = pyRedis.get_conn(settings.SPJ_KEY['all_files'])
    if all_spj_files is None:
        all_spj_files = {
            settings.SPJ_KEY['new_files']: [],
            "all_files": True
        }
    else:
        all_spj_files = json.loads(all_spj_files)
    all_spj_files[settings.SPJ_KEY['new_files']].append({"pid": pid})
    pyRedis.set_conn(settings.SPJ_KEY['all_files'], json.dumps(all_spj_files), None)


def update_problems(self, request_data, files, *args, **kwargs):
    pid: int = int(kwargs.get('pk'))
    # 备份测试数据
    if files is not None:
        backup_problems(files, pid)
    instance = self.get_queryset().get(pid=pid)
    serial = self.get_serializer(instance, data=request_data, partial=False)
    serial.is_valid(raise_exception=True)
    serial.save()
    pyRedis.DataSlice.update(problem_key, pid - 1000, serial.data, get_data)
    return serial


def create_problem(self, request_data, files):
    """
    创建题目
    :param files:
    :param self:
    :param request_data:
    :return:
    """
    pid = self.get_queryset().aggregate(Max("pid")).get("pid__max", None)
    if pid is None:
        pid = 1000  # 已1000为初始
    else:
        pid += 1
    serializer = self.get_serializer(data=request_data)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    data = {
        'pid': pid
    }
    models.Problems.objects.filter(pid=instance.pid).update(**data)
    if files is not None:
        backup_problems(files, pid)
    # 更新缓存数据
    data = serializer.data.copy()
    data['pid'] = pid
    pyRedis.DataSlice.delete(problem_key, pid - 1000)
    return pid


def spj_create(obj, request) -> Response:
    """
    创建相关信息于redis
    :param obj:
    :param request:
    :return:
    """
    serializer = obj.get_serializer(data=request.data)
    serializer.is_valid()

    data = serializer.data.copy()
    data['pid'] = request.data.get('pid', None)
    spj_pid_key = settings.SPJ_KEY['pid']
    pid = pyRedis.decrease(spj_pid_key)
    data[spj_pid_key] = "P%d" % pid
    # 临时存放点，滚动储存
    if pid >= -99:
        pyRedis.delete_key(spj_pid_key)
    data['name'] = "checker"
    validate_test_case(request.FILES)
    spj_file = request.FILES.getlist("spjFile")[0]
    spj_file.name = 'checker.cpp'

    pattern = tasks.get_spj_temp_root_path(data[spj_pid_key])
    ojFiles.save_bin(pattern, spj_file.name, spj_file.file)
    ojFiles.write_list_length(len(request.FILES.getlist("input")), pattern)
    spj_backup(request.FILES.getlist("input"), pattern, '', data[spj_pid_key])
    spj_backup(request.FILES.getlist("output"), pattern, '.out', data[spj_pid_key])
    task_id = tasks.compile_spj.delay(data)
    pyRedis.set_cache("%s_%s" % (settings.SPJ_KEY['prefix'], task_id.id), data, 86400)  # 一天
    return Response({'result': task_id.id, 'code': 1})


def send_checker_task(data: dict):
    check_task = {}
    for key in settings.SPJ_KEY['task_keys']:
        check_task[settings.SPJ_KEY['task_keys'][key]] = data[key]
    check_task['pid'] = int(check_task['pid'][1:len(check_task['pid'])])
    if isinstance(check_task['O2'], str):
        check_task['O2'] = bool(strtobool(check_task['O2']))
    oj_task.send_task.delay(check_task)


# TODO spj同步部分相关逻辑还需修改
class SpjProblems(GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin):
    """
    spj 相关
    """
    queryset = models.Problems.objects.all()
    serializer_class = serializers.AllProblemSerializer
    permission_classes = [permissions.IsAdminUser]

    def list(self, request, *args, **kwargs):
        """
        查询spj结果
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        task_id = request.query_params.get("task_id", None)
        if task_id is None:
            return Response({'result': "找不到该任务", 'code': 1})
        res = AsyncResult(task_id)
        task_result = res.result

        prob_info = pyRedis.get_cache("%s_%s" % (settings.SPJ_KEY['prefix'], task_id))
        if prob_info is not None and prob_info.get('result', None) is not None:
            task_result = prob_info['result']
        elif task_result is None or prob_info is None:
            return Response({'result': "找不到该任务", 'code': 1})

        if task_result > 0:  # 第一步
            path = tasks.get_spj_compile_info(prob_info[settings.SPJ_KEY['pid']])
            err_path = path['err_path']
            err = ojFiles.read_str(err_path, 1024)
            return Response({'result': '出现了错误', 'code': 2, 'err': err})
        if prob_info.get('has_set', False) is False:
            prob_info['result'] = task_result
            prob_info['has_set'] = True
            pyRedis.set_cache("%s_%s" % (settings.SPJ_KEY['prefix'], task_id), prob_info, 43200)
        if task_result < 0:  # 第二步
            return Response({'result': '等待结果', 'code': 1})
        return Response({'result': 'ok', 'code': 0, "data": json.dumps(prob_info)})

    def retrieve(self, request, *args, **kwargs):
        task_id = kwargs.get('pk', None)
        prob_id = request.query_params.get('prob_id', None)
        if task_id is None or prob_id is None:
            return Response({'result': '找不到该记录或题目,请重新提交代码', 'code': 1})
        task_info = pyRedis.get_cache("%s_%s" % (settings.SPJ_KEY['prefix'], task_id))
        prob_info = pyRedis.get_cache("%s_%s" % (settings.SPJ_KEY['prefix'], prob_id))
        if task_info is None or prob_info is None:
            return Response({'result': '找不到该记录或题目,请重新提交代码', 'code': 1})
        rtn_msg = "最新的提交并未通过"
        if task_info['accept'] == 0:
            pid = prob_info.get('pid', None)
            if pid is not None:
                pid = int(pid)
                # 更新标签
                ProblemsLabelView.update_labels(prob_info, True)
                prob_info['pid'] = int(pid)
                update_problems(self, prob_info, None, None, **{'pk': int(pid)})
            else:
                pid = create_problem(self, prob_info, None)
                ProblemsLabelView.update_labels(prob_info, False)

            prob_info['pid'] = pid
            # os.umask(0)
            tasks.cp_problems.delay(prob_info)
            # 删除相关信息
            pyRedis.delete_key("%s_%s" % (settings.SPJ_KEY['prefix'], task_id))
            pyRedis.delete_key("%s_%s" % (settings.SPJ_KEY['prefix'], prob_id))
            add_spj_problem_list(pid)
            rtn_msg = "已完成"

        return Response({'result': rtn_msg, 'code': task_info['accept']}, )

    def create(self, request, *args, **kwargs):
        """
        校验checker正确性
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        code = request.data.get('code', None)
        if code is None:
            return Response({'result': '不存在代码'})
        task_id = request.data.get("task_id", None)
        prob_info: dict = pyRedis.get_cache("%s_%s" % (settings.SPJ_KEY['prefix'], task_id))
        if task_id is None or prob_info is None:
            return Response({'result': "找不到该任务", 'code': 1})
        for key in request.data:
            prob_info[key] = request.data[key]
        prob_info['uuid'] = uuid.uuid4().hex
        prob_info['uid'] = request.user.id
        prob_info['pid'] = prob_info[settings.SPJ_KEY['pid']]
        send_checker_task(prob_info)
        return Response({'result': prob_info['uuid'], 'code': 0})


@method_decorator(gzip_page, name='dispatch')
class GetProblems(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = models.Problems.objects.all()
    serializer_class = serializers.AllProblemSerializer
    exclude_keys = {'cols', 'page'}
    get_fields = ('pid', 'title', 'acceptNum', 'submitNum')

    def list(self, request, *args, **kwargs):

        if len(request.query_params) > 2:  # 通过sql
            query_data = dict()
            for key in request.query_params:
                if key not in self.exclude_keys:
                    query_data[key] = request.query_params[key]

            query_res = self.get_queryset().filter(**query_data)
            try:
                value = self.get_serializer(util.slice_data2(request, query_res), many=True).data
            except MultiValueDictKeyError as e:
                return Response({'result': e.args})
            num = len(query_res)
        else:  # 通过redis
            num = pyRedis.get_cache('problems_total')
            if num is None:
                num = models.Problems.objects.count()
                pyRedis.set_cache("problems_total", num, 3600)
            try:
                value = util.slice_data(request, problem_key, get_data)  # problems.get('data')[start:end]
            except MultiValueDictKeyError as e:
                return Response({'result': e.args})
        total = {'total': num}
        value.insert(0, total)
        return Response(value)

    def retrieve(self, request, *args, **kwargs):
        # 已使用pid索引
        state = status.HTTP_200_OK
        cnt: str = kwargs.get('pk', '-1')
        if not cnt.isdigit() or int(cnt) - 1000 < 0:
            data = {'result': "找不到该题目"}
            state = status.HTTP_404_NOT_FOUND
        else:
            data = pyRedis.DataSlice.retrieve(problem_key, int(cnt) - 1000, get_data)
            if data is None:
                data = {'result': "找不到该题目"}
                state = status.HTTP_404_NOT_FOUND
        return Response(data, status=state)


class SaveProblems(ModelViewSet):
    queryset = models.Problems.objects.all()
    serializer_class = serializers.AllProblemSerializer
    permission_classes = [permissions.IsAdminUser]

    def retrieve(self, request, *args, **kwargs):
        return Response({'result': '不允许此调用'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def list(self, request, *args, **kwargs):
        return Response({'result': '不允许此调用'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({'result': '不允许此调用'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        """
        更新
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            # 记录相关信息,标签等信息在另一处更新
            pid: int = int(kwargs.get('pk'))
            new_file_flag = strtobool(request.data.get("newFile", False))
            if int(request.data.get("method", 0)) == 1:
                new_checker_flag = strtobool(request.data.get("newChecker", False))
                # 非仅修改题面
                if new_checker_flag or new_file_flag:
                    result = spj_create(self, request)
                    return result
            ProblemsLabelView.update_labels(request.data, pid=pid, update_flag=True)
            update_problems(self, request.data, request.FILES, *args, **kwargs)
            if new_file_flag:
                tasks.sync_problems(None)
        except ojExceptions.OJBaseError as e:
            return Response({'result': str(e), 'code': 1})
        return Response({'result': 'success', 'code': 0})

    def create(self, request, *args, **kwargs):
        try:
            # 记录相关信息,标签等信息在另一处更新
            if int(request.data.get("method", 0)) == 1:
                result = spj_create(self, request)
                return result
            else:
                # 更新标签
                ProblemsLabelView.update_labels(request.data)
                pid = create_problem(self, request.data, request.FILES)
                tasks.sync_problems(None)
        except ojExceptions.OJBaseError as e:
            return Response({'result': str(e), 'code': 1})
        # 通知更新文件

        return Response({'result': 'success', 'code': 0})


@method_decorator(gzip_page, name='dispatch')
class ProblemsLabelView(GenericViewSet, mixins.ListModelMixin):
    queryset = models.ProblemsLabel.objects.filter(count__gt=0)
    serializer_class = serializers.ProblemsLabelSerializer

    @classmethod
    def update_labels(cls, data, pid=None, update_flag=False):
        new_label: list[str] = data.get("label").split(',')
        old_label = []
        if update_flag:
            labels = models.Problems.objects.filter(pid=pid).values('label')[0]
            old_label = labels['label'].split(',')
        str_set = models.ProblemsLabel.unique_labels(new_label, [])
        models.ProblemsLabel.modify_labels(new_label, str_set, 1)
        if update_flag:
            models.ProblemsLabel.modify_labels(old_label, str_set, -1)


# TODO 比赛类，还在测试中
@method_decorator(gzip_page, name='dispatch')
class CompetitionView(ModelViewSet):
    queryset = models.Competition.objects.filter(isActive=True)
    serializer_class = serializers.CompetitionSerializer
    permission_classes = [ojPermission.IsAdminOrReadOnly]
    query_key = keys.get("competition")

    @classmethod
    def get_data(cls, start: int, size: int):
        problems = models.Competition.objects.all()
        serializer = serializers.CompetitionSerializer(problems, many=True)
        return serializer.data[start * size:(start + 1) * size]

    @classmethod
    def handle_problems(cls, request, method: util.Method):
        serializer_list = list()
        problem_list: list = request.get('problem_list', None)
        competition_only = True
        if method == util.Method.UPDATE:
            competition_only: bool = request.get('competition', False)  # 只修改比赛相关内容，不修改题目
        if problem_list is None and competition_only is False:
            raise ojExceptions.NoneDataError('没有题目')
        cnt = 0
        for problem in problem_list:
            problem['pid'] = cnt
            problem['competition_id'] = request.get('cid')
            problem['id'] = request.get('cid')
            serializer = serializers.CompetitionProblemSerializer(data=problem)
            if serializer.is_valid(raise_exception=True):
                serializer_list.append(serializer)  # 合法的保存
            cnt += 1
        return serializer_list

    @classmethod
    def serializer_request(cls, request) -> list:
        problem_count: int = int(request.data.get('problemCount', 0))
        data_list = list()
        if problem_count <= 0:
            raise ValueError('题目数量不可小于0')
        for cnt in range(0, problem_count):
            str_pattern = 'problem[%d]' % cnt
            problem_detail = json.loads(request.data.get(str_pattern, ''))
            problem_detail['timeLimit'] = problem_detail['info']['limits'][0]['timeLimit']
            problem_detail['memoryLimit'] = problem_detail['info']['limits'][0]['memoryLimit']

            data_list.append(problem_detail)
        return data_list

    # 现只有接口(不正确)，前端未完成
    def update(self, request, *args, **kwargs):
        try:
            cnt = kwargs.get('pk')
            cnt = int(cnt) - 1
            serializer_list = self.handle_problems(request.data, util.Method.UPDATE)
        except Exception as e:
            return Response({'result': e.args})
        # 更新中的条件不能这样
        backup_problems(request, request.data.get("pid", None), kwargs.get('pk'))
        response = super().update(request, args, kwargs)
        for serial in serializer_list:
            serial.save()
        pyRedis.DataSlice.update(self.query_key, cnt, response.data, self.get_data)
        return response

    def create(self, request, *args, **kwargs):
        try:
            problem_list = self.serializer_request(request)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            request.data['problem_list'] = problem_list
            cid = models.Competition.objects.all().aggregate(Max('id'))
            cid = cid.get('id__max', None)
            if cid is None:
                cid = 1
            else:
                cid += 1
            request.data['cid'] = cid
            serializer_list = self.handle_problems(request.data, util.Method.CREATE)
        except Exception as e:
            return Response({'result': e.args})

        for cnt in range(0, int(request.data.get("problemCount", 0))):
            files: MultiValueDict = MultiValueDict()
            files.setlist("input", request.FILES.getlist("problem[%d][input]" % cnt))
            files.setlist("output", request.FILES.getlist("problem[%d][output]" % cnt))
            backup_problems(files, cnt, cid)

        # return Response({'result': '测试中'})
        for serial in serializer_list:
            serial.save()
        serializer.save()
        # 保存比赛信息
        pyRedis.DataSlice.create(self.query_key, cid, serializer.data, self.get_data)
        # TODO Redis中保存题目信息
        return Response({'result': '已创建'})

    def list(self, request, *args, **kwargs):
        num = pyRedis.get_cache("competition_total")
        try:
            value = list(filter(serializers.CompetitionSerializer.is_active,
                                util.slice_data(request, self.query_key, self.get_data)))
        except MultiValueDictKeyError as e:
            return Response({'result': e.args})
        if num is None:
            num = len(value)
            pyRedis.set_cache("competition_total", num, 3600)
        total = {'total': num}
        value.insert(0, total)
        return Response(value)

    # 同上
    def retrieve(self, request, *args, **kwargs):
        state = status.HTTP_200_OK
        cnt = kwargs.get('pk', None)
        if cnt is not None:
            data = pyRedis.DataSlice.retrieve(self.query_key, int(cnt) - 1, self.get_data)  # 从1开始的
            if data is None:
                data = {'result': "找不到该题目"}
                state = status.HTTP_404_NOT_FOUND
        else:
            data = {'result': "找不到该题目"}
            state = status.HTTP_404_NOT_FOUND
        return Response(data, status=state)
        # return super().retrieve(request, args, kwargs)

    # TODO 删除设置isActive为false
    def destroy(self, request, *args, **kwargs):
        return Response({'result': '不允许此操作'})


class CompetitionProblemView(GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin):
    """
    比赛的题目详情页，仅允许管理修改
    """
    queryset = models.CompetitionProblems.objects.all()
    serializer_class = serializers.CompetitionProblemSerializer
    permission_classes = [ojPermission.IsAdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        self.queryset = models.CompetitionProblems.objects.filter(
            competition_id=request.query_params.get("competition_id", ''))
        return super().list(request, args, kwargs)

    def retrieve(self, request, *args, **kwargs):
        try:
            timeUtil.check_time(request.query_params, 'g')
        except Exception as e:
            return Response({'result': e.args}, status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, args, kwargs)


@method_decorator(gzip_page, name='dispatch')
class CompetitionRankView(GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin):
    queryset = models.CompetitionRank.objects.all()
    serializer_class = serializers.CompetitionRankSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def create(self, request, *args, **kwargs):
        data_copy = request.data.copy()
        data_copy['submitter'] = request.user.username
        data_copy['submitter_id'] = request.user.id
        data_copy['id'] = 1
        serializer = self.get_serializer(data=data_copy)
        serializer.is_valid(raise_exception=True)
        if self.get_queryset().filter(id=serializer.validated_data['id']).first() is not None:
            return Response({"result": "已报名"})
        self.perform_create(serializer)
        return Response({"result": "报名成功"}, status=status.HTTP_201_CREATED)

    # TODO 待制作分页
    def list(self, request, *args, **kwargs):
        cid = request.query_params.get('cid', None)
        if cid is not None:
            self.queryset = self.get_queryset().filter(competition_id=cid)
        else:
            return Response({"result": "未知的参数"})
        return super().list(request, args, kwargs)
