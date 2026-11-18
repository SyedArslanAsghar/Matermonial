from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("phone_number",)


class AdminUserChangeForm(DjangoUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
