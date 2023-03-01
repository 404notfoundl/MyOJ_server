class OJBaseError(Exception):
    def __init__(self, name: str, reason: str):
        super().__init__(self)
        self.name = name
        self.reason = reason

    def __str__(self):
        return "%s:%s" % (self.name, self.reason)


class FileInvalidError(OJBaseError):
    def __init__(self, reason):
        super().__init__("文件不合法", reason)


class NoneDataError(OJBaseError):
    def __init__(self, reason):
        super().__init__('不存在数据', reason)


class SpjCompileError(OJBaseError):
    def __init__(self, reason):
        super(SpjCompileError, self).__init__('spj文件编译出错', reason)
