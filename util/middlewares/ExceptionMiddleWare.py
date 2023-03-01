import redis
from django.middleware.common import MiddlewareMixin
from rest_framework.response import Response


class ExceptionMiddleware(MiddlewareMixin):
    """统一异常处理中间件"""

    def process_exception(self, request, exception: Exception):
        """
        统一异常处理
        :param request: 请求对象
        :param exception: 异常对象
        :return:
        """
        # 异常处理
        print(exception, type(exception))
        if isinstance(exception, redis.exceptions.TimeoutError):
            return Response({"result": "可能是服务器内部出现了网络问题，请稍后重试"})
        return None
