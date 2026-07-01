from django.shortcuts import redirect
from functools import wraps

def firebase_login_required(view_func):
    """
    Decorator for views that checks that the user is logged in via Firebase,
    redirecting to the log-in page if necessary.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('firebase_user'):
            return redirect('cms:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
