import smtplib
import logging
from email.mime.text import MIMEText

from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import status
from . import pyRedis
from enum import Enum

from django.core.mail import send_mail


def site_log(logger_name: str):
    return logging.getLogger(logger_name)


def slice_data(request, data_key: str, call):
    """
    分页功能,通过redis的
    :param call:
    :param data_key:
    :param request: 请求
    :return: 切割后数据
    """
    try:
        page = int(request.query_params['page'])
        cols = int(request.query_params['cols'])
    except MultiValueDictKeyError as e:
        raise MultiValueDictKeyError('未知的分页')
    start = (page - 1) * cols
    return pyRedis.DataSlice.get(data_key, start, cols, call)


def slice_data2(request, data: list):
    """
    分页功能
    :param data:
    :param request: 请求
    :return: 切割后数据
    """
    try:
        page = int(request.query_params['page'])
        cols = int(request.query_params['cols'])
    except MultiValueDictKeyError as e:
        raise MultiValueDictKeyError('未知的分页')
    start = (page - 1) * cols
    end = page * cols
    return data[start:end]


def split_str(data: str, char: str):
    """
    反向分割第一个指定字符，返回前面的切片
    :param data:
    :param char:
    :return:
    """
    str_len = len(data)
    for cnt in range(0, str_len):
        if data[str_len - cnt - 1] == char:
            return data[0:str_len - cnt - 1]
    return data


class Method(Enum):
    GET = 0
    UPDATE = 1
    POST = 2
    DELETE = 3
    CREATE = 4


class FieldsType(Enum):
    T_STR = 0
    T_INT = 1
    T_BOOL = 2


class SiteEMail:
    title = "请继续以完成注册"
    template_str = '''
            <h1>感谢您的注册，请点击以下链接以完成注册</h1> \n
            <h2>有效时间：1 小时,请及时验证</h2>\n
            <a href="{0}">{0}</a>            
    '''
    timeout = 3600

    @classmethod
    def send_link(cls, to_email, link):
        if to_email is None:
            raise ValueError("目的地址不能为空")
        res = True
        try:
            msg = MIMEText(cls.template_str.format(link), 'html', 'utf-8')
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = cls.title
            smtp = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
            # smtp.connect(settings.EMAIL_HOST, settings.EMAIL_PORT)
            smtp.ehlo("smtp.qq.com")
            smtp.login(settings.EMAIL_FROM, settings.EMAIL_HOST_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
            smtp.quit()
        except Exception as e:
            site_log("django.request").warning("send email failed: {}".format(e.args))
            res = False
        return res
