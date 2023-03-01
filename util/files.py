import _io
import os.path
import os

from django.core.files.storage import FileSystemStorage
from django.conf import settings

root_dir = FileSystemStorage(directory_permissions_mode=0o777)


def save_to_local(name, file, overwrite=True):
    """
    保存至本地，根目录为MEDIA_ROOT
    :param name: 相对路径
    :param file: 待保存文件
    :param overwrite: 是否覆盖，不覆盖则生成相似文件名
    :return:
    """
    if root_dir.exists(name) and overwrite:
        root_dir.delete(name)
    root_dir.save(name, file)
    # print('save to %s' % name)


def write_list_length(list_len: int, path: str):
    """
    写入对应测试组的测试点数量
    :param list_len:
    :param path: 完整路径
    :return:
    """
    if not os.path.exists(path):
        os.makedirs(path)
    path += '/__len__'
    list_len_file = open(path, mode="w")
    list_len_file.write(str(list_len))
    list_len_file.flush()
    list_len_file.close()


def save_bin(path: str, name: str, data: _io.BytesIO):
    os.makedirs(path, exist_ok=True)
    file = open("%s/%s" % (path, name), "wb")
    file.write(data.getvalue())
    file.flush()
    file.close()


def save_str(path: str, name: str, data: str):
    os.makedirs(path, exist_ok=True)
    file = open("%s/%s" % (path, name), "w", encoding='utf-8')
    file.write(data)
    file.flush()
    file.close()


def read_str(path: str, max_len: int):
    if os.path.exists(path):
        file = open(path, 'r', encoding='utf-8')
        rtn = file.read(max_len)
        file.close()
    else:
        rtn = ''
    return rtn
