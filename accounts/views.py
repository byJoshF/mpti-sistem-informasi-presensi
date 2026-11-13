from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponseForbidden
from .models import User
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .forms import (
    StudentRegistrationForm,
    UserLoginForm,
    ProfileUpdateForm,
)


def student_register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            return render(
                request,
                "accounts/register_success.html",
                {"user": user}
            )
    else:
        form = StudentRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


def user_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:login_success")

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            return redirect("accounts:login_success")
    else:
        form = UserLoginForm(request)

    return render(request, "accounts/login.html", {"form": form})


@login_required
def login_success(request):
    return render(
        request,
        "accounts/login_success.html",
        {"user": request.user}
    )


@require_POST
def user_logout(request):
    logout(request)
    return redirect("accounts:login")

@login_required
def student_profile(request):
    # Profil ini khusus untuk mahasiswa.
    if request.user.role != User.Role.STUDENT or request.user.is_superuser:
        return HttpResponseForbidden(
            "Halaman ini hanya dapat diakses mahasiswa."
        )

    if request.method == "POST":
        form = ProfileUpdateForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():
            form.save()

            return render(
                request,
                "accounts/profile.html",
                {
                    "form": ProfileUpdateForm(instance=request.user),
                    "success": True,
                    "user": request.user,
                }
            )
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "user": request.user,
        }
    )

@login_required
def student_password_change(request):
    if request.user.role != User.Role.STUDENT or request.user.is_superuser:
        return HttpResponseForbidden(
            "Halaman ini hanya dapat diakses mahasiswa."
        )

    if request.method == "POST":
        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():
            user = form.save()

            # Mempertahankan sesi login setelah password berubah.
            update_session_auth_hash(request, user)

            return render(
                request,
                "accounts/password_change.html",
                {
                    "form": PasswordChangeForm(user),
                    "success": True,
                }
            )
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "accounts/password_change.html",
        {"form": form}
    )