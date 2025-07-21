from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test

def merchant_required(function):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == 'merchant',
        login_url='/accounts/login/'
    )
    return actual_decorator(function)