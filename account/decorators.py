from functools import wraps
from django.shortcuts import redirect


def simple_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("simple_auth_ok"):
            return redirect("simple_login")
        return view_func(request, *args, **kwargs)
    return _wrapped_view