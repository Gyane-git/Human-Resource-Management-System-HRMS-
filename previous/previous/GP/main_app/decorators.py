from django.shortcuts import redirect
from django.contrib import messages

def ceo_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == '1':  # Assuming 1 is CEO
            return view_func(request, *args, **kwargs)
        messages.error(request, "You don't have permission to access this page.")
        return redirect('login')
    return wrapper

def employee_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == '3':  # 3 is Employee
            return view_func(request, *args, **kwargs)
        messages.error(request, "You don't have permission to access this page.")
        return redirect('login')
    return wrapper