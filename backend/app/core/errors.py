"""自定义异常与错误码"""
from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    RATE_LIMITED = 429
    INTERNAL = 500
    SERVICE_UNAVAILABLE = 503


class AppException(Exception):
    def __init__(self, code: ErrorCode, message: str, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(ErrorCode.NOT_FOUND, message)


class BadRequestError(AppException):
    def __init__(self, message: str = "请求参数错误"):
        super().__init__(ErrorCode.BAD_REQUEST, message)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(ErrorCode.UNAUTHORIZED, message)
