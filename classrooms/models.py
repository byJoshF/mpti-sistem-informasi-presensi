
from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string


def generate_join_code():
    """Membuat kode gabung enam karakter secara acak."""
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    digits = "23456789"

    return (
        get_random_string(1, allowed_chars=letters)
        + get_random_string(1, allowed_chars=digits)
        + get_random_string(1, allowed_chars=letters)
        + get_random_string(1, allowed_chars=digits)
        + get_random_string(1, allowed_chars=letters)
        + get_random_string(1, allowed_chars=digits)
    )


class Classroom(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="classrooms",
        limit_choices_to={"role": "TEACHER"},
        verbose_name="Dosen pengampu"
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Nama kelas"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Deskripsi"
    )

    join_code = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        verbose_name="Kode gabung"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Tanggal dibuat"
    )

    def save(self, *args, **kwargs):
        if not self.join_code:
            for _ in range(10):
                code = generate_join_code()

                if not Classroom.objects.filter(join_code=code).exists():
                    self.join_code = code
                    break
            else:
                raise RuntimeError(
                    "Gagal membuat kode gabung yang unik."
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.join_code})"


class Enrollment(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Kelas"
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="class_enrollments",
        limit_choices_to={"role": "STUDENT"},
        verbose_name="Mahasiswa"
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Tanggal bergabung"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Status keanggotaan"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "student"],
                name="unique_student_enrollment_per_class"
            )
        ]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.student.username} - {self.classroom.name}"
