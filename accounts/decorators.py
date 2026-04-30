from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def role_required(*roles):
    """
    Usage:
        @role_required('teacher')
        @role_required('dekan', 'admin')   # multiple roles allowed
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def teacher_required(view_func):
    return role_required('teacher')(view_func)

def dekan_required(view_func):
    return role_required('dekan')(view_func)

def admin_required(view_func):
    return role_required('admin')(view_func)