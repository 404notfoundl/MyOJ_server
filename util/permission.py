from functools import update_wrapper
from rest_framework import permissions as base_permissions


def permission_classes(oj_permission_classes):
    def decorator(func):
        func.permission_classes = oj_permission_classes
        return func

    return decorator


def wrap_permission(*permissions, validate_permission=True):
    """
    custom permissions for special route
    自定义权限
    :param permissions: 权限类
    :param validate_permission:
    :return:
    """

    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            self.permission_classes = permissions
            if validate_permission:
                self.check_permissions(request)
            return func(self, request, *args, **kwargs)

        return update_wrapper(wrapper, func)

    return decorator


class IsVbAdminUser(base_permissions.IsAdminUser):
    """
    Allows access only to admin users.
    """

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return self.has_permission(request, view)


class IsUserSelf(base_permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.id != obj.id:
            return False
        return True


class IsAdminOrReadOnly(base_permissions.IsAdminUser):
    def has_permission(self, request, view):
        return bool(
            request.method in base_permissions.SAFE_METHODS or
            request.user and
            request.user.is_superuser
        )

