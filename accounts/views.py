
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .models import User
from .forms import (
    StudentRegistrationForm,
    UserLoginForm,
    ProfileUpdateForm,
)


def is_ajax_request(request):
    return (
        request.headers.get("x-requested-with")
        == "XMLHttpRequest"
    )


def ajax_form_error(request, template_name, context):
    html = render_to_string(
        template_name,
        context,
        request=request
    )

    return JsonResponse(
        {
            "success": False,
            "html": html,
        },
        status=400
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
        return redirect("home")

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            return redirect("home")
    else:
        form = UserLoginForm(request)

    return render(
        request,
        "accounts/login.html",
        {"form": form}
    )


@login_required
def login_success(request):
    return redirect("home")


@require_POST
def user_logout(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def student_profile(request):

    if (
        request.user.role != User.Role.STUDENT
        or request.user.is_superuser
    ):
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

            success_message = (
                "Profil berhasil diperbarui."
            )

            messages.success(
                request,
                success_message
            )

            if is_ajax_request(request):
                return JsonResponse({
                    "success": True,
                    "message": success_message,
                })

            return redirect("accounts:profile")

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "accounts/partials/profile_modal.html",
                {
                    "form": form,
                    "user": request.user,
                    "action_url": request.path,
                }
            )

    else:
        form = ProfileUpdateForm(
            instance=request.user
        )

    context = {
        "form": form,
        "user": request.user,
        "action_url": request.path,
    }

    if request.GET.get("modal") == "1":
        return render(
            request,
            "accounts/partials/profile_modal.html",
            context
        )

    return render(
        request,
        "accounts/profile.html",
        context
    )


@login_required
def student_password_change(request):

    if (
        request.user.role != User.Role.STUDENT
        or request.user.is_superuser
    ):
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

            update_session_auth_hash(
                request,
                user
            )

            success_message = (
                "Password berhasil diperbarui."
            )

            messages.success(
                request,
                success_message
            )

            if is_ajax_request(request):
                return JsonResponse({
                    "success": True,
                    "message": success_message,
                })

            return redirect("accounts:profile")

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "accounts/partials/password_change_modal.html",
                {
                    "form": form,
                    "action_url": request.path,
                }
            )

    else:
        form = PasswordChangeForm(request.user)

    context = {
        "form": form,
        "action_url": request.path,
    }

    if request.GET.get("modal") == "1":
        return render(
            request,
            "accounts/partials/password_change_modal.html",
            context
        )

    return render(
        request,
        "accounts/password_change.html",
        context
    )
