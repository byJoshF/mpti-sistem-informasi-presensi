
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Mahasiswa"
        TEACHER = "TEACHER", "Dosen"

    full_name = models.CharField(
        max_length=150,
        verbose_name="Nama lengkap"
    )

    email = models.EmailField(
        unique=True,
        verbose_name="Alamat email"
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="Peran pengguna"
    )

    REQUIRED_FIELDS = ["email", "full_name"]

    def __str__(self):
        return self.username
