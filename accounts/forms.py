from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from .models import User

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='邮箱')
    role = forms.ChoiceField(
        choices=[('customer', 'Customer'), ('merchant', 'Merchant')],
        label='角色'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("该邮箱已被注册。")
        return email

# forms.py
class UserEditForm(forms.ModelForm):
    old_password = forms.CharField(
        label='旧密码',
        widget=forms.PasswordInput,
        required=False,  # 保持非必填
        help_text='留空表示不修改密码'  # 添加提示
    )
    new_password1 = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput,
        required=False,
        help_text='至少8个字符'
    )
    new_password2 = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'role']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("该邮箱已被其他用户注册。")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("该用户名已被其他用户使用。")
        return username

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        # 只有当用户尝试修改密码时才进行验证
        if new_password1 or new_password2 or old_password:
            if not all([old_password, new_password1, new_password2]):
                self.add_error(None, "修改密码需填写所有密码字段")
            elif new_password1 != new_password2:
                self.add_error('new_password2', "两次输入的新密码不一致")
            elif not self.instance.check_password(old_password):
                self.add_error('old_password', "旧密码错误")

        return cleaned_data