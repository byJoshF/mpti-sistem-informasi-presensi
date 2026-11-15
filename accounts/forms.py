from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User


class StudentRegistrationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ("username", "full_name", "email")

        labels = {
            "username": "NIM",
            "full_name": "Nama lengkap",
            "email": "Alamat email",
        }

    def save(self, commit=True):
        user = super().save(commit=False)

        # Pendaftar otomatis menjadi mahasiswa.
        user.role = User.Role.STUDENT

        if commit:
            user.save()

        return user


class UserLoginForm(AuthenticationForm):
    role = forms.ChoiceField(
        choices=[
            (User.Role.STUDENT, "Mahasiswa"),
            (User.Role.TEACHER, "Dosen"),
        ],
        initial=User.Role.STUDENT,
        label="Masuk sebagai",
    )

    username = forms.CharField(
        label="NIM / Username / Email"
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput()
    )

    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password")
        role = self.cleaned_data.get("role")

        if identifier and password and role:
            login_identifier = identifier

            # Dosen boleh login menggunakan email.
            if role == User.Role.TEACHER and "@" in identifier:
                teacher = User.objects.filter(
                    email__iexact=identifier,
                    role=User.Role.TEACHER
                ).first()

                login_identifier = teacher.username if teacher else None

            user = None

            if login_identifier:
                user = authenticate(
                    self.request,
                    username=login_identifier,
                    password=password
                )

            if (
                user is None
                or user.role != role
                or user.is_superuser
            ):
                raise ValidationError(
                    "Identitas, peran, atau password tidak sesuai."
                )

            self.confirm_login_allowed(user)
            self.user_cache = user

        return self.cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "email")

        labels = {
            "full_name": "Nama lengkap",
            "email": "Alamat email",
        }