import math

from django.core.cache import cache
from django.conf import settings
from django_redis import get_redis_connection


def get_cache(key: str):
    """
    get 带前缀
    :param key:
    :return:
    """
    data = cache.get(key)
    return data


def get_conn(key):
    """
    get 不带前缀
    :param key:
    :return:
    """
    conn = get_redis_connection()
    return conn.get(key)


def set_cache(key: str, value, time=60):
    """
    set 带前缀
    :param key:
    :param value:
    :param time: 秒
    :return:
    """
    cache.set(key, value, timeout=time)


def set_conn(key, value, time=60):
    """
    set 不带前缀
    :param key:
    :param value:
    :param time:
    :return:
    """
    conn = get_redis_connection()
    conn.set(key, value)
    if time is not None:
        conn.expire(key, time)
    else:
        conn.persist(key)


def delete_key(key: str):
    cache.delete_pattern(key)


def delete_conn(key: str):
    conn = get_redis_connection()
    conn.delete(key)


def subscribe(key: str):
    conn = get_redis_connection()
    conn.subscribe(key)


def publish(key: str, value: str):
    conn = get_redis_connection()
    conn.publish(key, value)


def increase(key: str):
    conn = get_redis_connection()
    return conn.incr(key)


def decrease(key: str):
    conn = get_redis_connection()
    return conn.decr(key)


class DataSlice:
    """
    将数据切块存入redis，
    默认大小settings.CHUNK_SIZE
    注意，此类中数据必须连续有序才能正确读取
    """
    chunk_size: int = settings.CHUNK_SIZE
    ttl = 7200

    @classmethod
    def delete(cls, data_key, index='*'):
        if index != '*':
            index = cls.slice(int(index))
        delete_key(data_key)
        delete_key("%s_%s" % (data_key, index))

    @classmethod
    def set_all(cls, data_list: list, data_key: str):
        """
        设置全部，[data_key]_total 表示data_list长度
        :param data_list:
        :param data_key:
        :return:
        """
        list_len = len(data_list)
        pages: int = math.ceil(list_len / cls.chunk_size)
        for cnt in range(0, pages):
            # redis_key = data_key + "_%d" % cnt
            # set_cache(redis_key, data_list[cnt * cls.chunk_size: (cnt + 1) * cls.chunk_size], cls.ttl)
            cls.set(data_list[cnt * cls.chunk_size: (cnt + 1) * cls.chunk_size], data_key, cnt)
        set_cache(data_key + "_total", list_len, cls.ttl)
        set_cache(data_key, True, cls.ttl)

    @classmethod
    def set(cls, data_list: list, data_key: str, index: int):
        """
        更新指定块的数据
        :param data_list:
        :param data_key:
        :param index:
        :return:
        """
        redis_key = data_key + "_%d" % index
        set_cache(redis_key, data_list, cls.ttl)

    @classmethod
    def get_chunk(cls, key: str, index: int, call) -> list:
        data: list = get_cache(key + "_%d" % index)
        if data is None and call is not None:
            data = call(index, cls.chunk_size)
            if len(data) != 0:
                cls.set(data, key, index)
        return data

    @classmethod
    def get_keys(cls, key):
        return cache.keys(key + "_*")

    @classmethod
    def get(cls, data_key: str, start: int, number: int, call):
        left = int(start / cls.chunk_size)
        end = start + number
        right = int(end / cls.chunk_size)
        right = right + 1
        data_list = list()
        for cnt in range(left, right):
            start_index = 0
            end_index = cls.chunk_size
            if cnt == left:
                start_index = start % cls.chunk_size
            if cnt == right - 1:
                end_index = end % cls.chunk_size
            data = cls.get_chunk(data_key, cnt, call)
            if data is not None:
                data_list.extend(data[start_index:end_index])
        return data_list

    @classmethod
    def retrieve(cls, data_key: str, index: int, call):
        """
        获取data_key中第index个元素
        :param call:
        :param data_key: 键
        :param index: 下标
        :return: 该元素
        """
        start = cls.slice(index)
        cnt = index - start * cls.chunk_size
        data = cls.get_chunk(data_key, start, call)
        if cnt >= len(data) or data is None:
            return None
        return data[cnt]

    @classmethod
    def update(cls, data_key: str, index: int, data, call):
        start = cls.slice(index)
        cnt = index - start * cls.chunk_size
        data_obj = cls.get_chunk(data_key, start, call)
        if data_obj is not None:
            data_obj[cnt] = data
            cls.set(data_obj, data_key, start)

    @classmethod
    def slice(cls, index: int):
        """
        将索引切块
        :param index:
        :return:块数，向下取整
        """
        return int(index / cls.chunk_size)

    @classmethod
    def create(cls, data_key, index, data, call):
        start = cls.slice(index)
        data_obj = cls.get_chunk(data_key, start, call)
        if data_obj is not None:
            data_obj.append(data)
            cls.set(data_obj, data_key, start)
