from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.student_register, name="register"),
    path("login/", views.user_login, name="login"),
    path("login/berhasil/", views.login_success, name="login_success"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.student_profile, name="profile"),
    path("password/change/", views.student_password_change, name="password_change"),
]