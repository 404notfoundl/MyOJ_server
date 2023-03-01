import math

from rest_framework.pagination import PageNumberPagination, CursorPagination
from . import pyRedis


class OjPagination(PageNumberPagination):
    page_size = 10  # default page size
    page_size_query_param = 'cols'  # ?page=xx&cols=??
    # max_page_size = 10  # max page size


class TaskPagination(CursorPagination):
    page_size = 10  # default page size
    page_size_query_param = 'cols'  # ?page=xx&cols=??
    cursor_query_param = 'cursor'  # Default is cursor
    ordering = '-submitDate'


