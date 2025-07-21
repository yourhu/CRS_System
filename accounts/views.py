from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserEditForm


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '注册成功！欢迎加入 CRS 系统。')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def form_invalid(self, form):
        messages.error(self.request, '用户名或密码错误，请重试。')
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    template_name = 'accounts/logout.html'

@login_required
def change_password(request):
    return render(request, 'accounts/change_password.html')


# views.py
from django.contrib.auth import update_session_auth_hash


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()

            # 仅在修改密码时更新密码和会话
            new_password = form.cleaned_data.get('new_password1')
            if new_password:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)  # 保持登录状态
                messages.success(request, '密码已成功修改！')
            else:
                messages.success(request, '个人信息已更新')

            return redirect('edit_profile')
        else:
            # 打印调试信息（开发环境）
            print(form.errors)
    else:
        form = UserEditForm(instance=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})