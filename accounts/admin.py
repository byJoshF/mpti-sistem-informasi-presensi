
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Kolom daftar pengguna
    list_display = (
        "username",
        "full_name",
        "email",
        "role",
        "is_staff",
        "is_active",
    )

    # Filter kategori
    list_filter = (
        "role",
        "is_staff",
        "is_active",
    )

    # Fitur pencarian pengguna
    search_fields = (
        "username",
        "full_name",
        "email",
    )

    # Mengatur informasi edit akun
    fieldsets = UserAdmin.fieldsets + (
        ("Informasi Tambahan", {
            "fields": ("full_name", "role"),
        }),
    )

    # Mengatur informasi ketika administrator membuat akun baru
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informasi Tambahan", {
            "fields": ("full_name", "email", "role"),
        }),
    )
