# utils/decorators.py
from django.http import HttpResponseForbidden

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                return HttpResponseForbidden("Access Denied")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
