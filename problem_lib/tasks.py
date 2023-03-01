# Create your tasks here
from __future__ import absolute_import, unicode_literals

import json
import os
import re
import shutil
import subprocess
from util import util, pyRedis
from django.conf import settings
from online_judge.celery import app
from . import models

compiler_path = "/root/projects/judger/compiler"
runner_path = ""
spj_file_template = {
    "pid": 0,
    # "cid":0
}


def get_spj_temp_root_path(path):
    return '%s/%s' % (settings.MEDIA_ROOT, path)


def get_spj_compile_info(path: str):
    """

    :param path: 相对路径，task_id
    :return:
    """
    root_path = get_spj_temp_root_path(path)
    return {
        'O2': True,
        'src_path': os.path.abspath('%s/checker.cpp' % root_path),
        'err_path': os.path.abspath('%s/checker.err' % root_path),
        'des_path': os.path.abspath('%s/checker' % root_path),
        'lang': 'cpp11'
    }


def get_shell_cmd(info: dict, cmd):
    for key in info:
        cmd = "%s --%s %s" % (cmd, key, int(info[key]) if isinstance(info[key], bool) else info[key])
    return cmd


def sync_problems(pid: int, cid: int = None):
    spj_list = {
        settings.SPJ_KEY['new_files']: [
        ]
    }
    if pid is not None:
        spj_list[settings.SPJ_KEY['new_files']].append({"pid": int(pid)})
    if cid is not None:
        spj_list[settings.SPJ_KEY['new_files']][0]['cid'] = int(cid)
    pyRedis.publish(settings.SPJ_KEY['new_files'], json.dumps(spj_list))


@app.task
def test(cmd):
    return subprocess.call(cmd)


@app.task
def test_mkdir(path):
    old = os.umask(0)
    os.makedirs(path, 0o777)
    os.umask(old)


@app.task
def compile_spj(data) -> int:
    res = 0
    if settings.IS_LINUX:
        res = os.system(get_shell_cmd(get_spj_compile_info(data[settings.SPJ_KEY['pid']]), compiler_path))
    if res == 0:
        pid = data[settings.SPJ_KEY['pid']]
        pid = int(pid[1:len(pid)])
        sync_problems(pid)
    return res


pattern = re.compile(r"(P)-\d+(_\d+[.,\w]*)")  # P-***_* 改名用模式串


@app.task
def cp_problems(data):
    prob_root_path = os.path.abspath('%s/P%s/' % (settings.MEDIA_ROOT, data['pid']))
    temp_root_path = os.path.abspath('%s' % get_spj_temp_root_path(data[settings.SPJ_KEY['pid']]))
    if not os.path.exists(prob_root_path):
        old = os.umask(0)
        os.makedirs(prob_root_path, 0o777)
        os.umask(old)
    if os.path.exists(temp_root_path):
        for root, dirs, files in os.walk(temp_root_path):
            for file in files:
                # 格式化名称
                new_file = os.path.join(prob_root_path,
                                        re.sub(pattern, r"\1 %s\2" % data['pid'], file).replace(' ', ''))
                src_file = os.path.join(root, file)
                shutil.copy(src_file, new_file)
        sync_problems(int(data['pid']))
    else:
        print('temp spj path not exist')
    print("cp problems")
    return 0

