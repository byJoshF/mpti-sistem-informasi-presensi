
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.crypto import get_random_string

from classrooms.models import Classroom


def generate_attendance_code():
    """Membuat kode absensi enam karakter secara acak."""
    allowed_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    return get_random_string(
        length=6,
        allowed_chars=allowed_chars
    )


class AttendanceSession(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Terbuka"
        CLOSED = "CLOSED", "Ditutup"
        EXPIRED = "EXPIRED", "Kedaluwarsa"
        CANCELLED = "CANCELLED", "Dibatalkan"
        FINAL = "FINAL", "Final"

    DURATION_CHOICES = [
        (5, "5 menit"),
        (10, "10 menit"),
        (15, "15 menit"),
        (20, "20 menit"),
        (30, "30 menit"),
    ]

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
        verbose_name="Kelas"
    )

    meeting_number = models.PositiveIntegerField(
        editable=False,
        verbose_name="Nomor pertemuan"
    )

    attendance_code = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        verbose_name="Kode absensi"
    )

    duration_minutes = models.PositiveSmallIntegerField(
        choices=DURATION_CHOICES,
        verbose_name="Durasi sesi (menit)"
    )

    started_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Waktu mulai"
    )

    expires_at = models.DateTimeField(
        editable=False,
        verbose_name="Waktu berakhir"
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Waktu ditutup"
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Status sesi"
    )

    cancellation_reason = models.TextField(
        blank=True,
        verbose_name="Alasan pembatalan"
    )

    def save(self, *args, **kwargs):
        if self._state.adding:
            # Membuat nomor pertemuan otomatis.
            if not self.meeting_number:
                last_number = (
                    AttendanceSession.objects
                    .filter(classroom=self.classroom)
                    .aggregate(max_number=Max("meeting_number"))
                    ["max_number"]
                    or 0
                )
                self.meeting_number = last_number + 1

            # Membuat kode absensi yang belum digunakan.
            if not self.attendance_code:
                for _ in range(10):
                    code = generate_attendance_code()

                    if not AttendanceSession.objects.filter(
                        attendance_code=code
                    ).exists():
                        self.attendance_code = code
                        break
                else:
                    raise RuntimeError(
                        "Gagal membuat kode absensi yang unik."
                    )

            # Menghitung waktu berakhir berdasarkan durasi.
            if not self.expires_at:
                self.expires_at = (
                    self.started_at
                    + timedelta(minutes=self.duration_minutes)
                )

        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "meeting_number"],
                name="unique_meeting_number_per_class"
            ),
            models.UniqueConstraint(
                fields=["classroom"],
                condition=Q(status="OPEN"),
                name="one_open_session_per_class"
            ),
        ]
        ordering = ["-meeting_number"]

    def __str__(self):
        return (
            f"{self.classroom.name} - "
            f"Pertemuan {self.meeting_number}"
        )


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Hadir"
        NOT_SUBMITTED = "NOT_SUBMITTED", "Belum Mengisi"
        PERMITTED = "PERMITTED", "Izin"
        SICK = "SICK", "Sakit"
        ABSENT = "ABSENT", "Alfa"

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.PROTECT,
        related_name="attendance_records",
        verbose_name="Sesi absensi"
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_records",
        limit_choices_to={"role": "STUDENT"},
        verbose_name="Mahasiswa"
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.NOT_SUBMITTED,
        verbose_name="Status kehadiran"
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Waktu mengisi"
    )

    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="finalized_attendance_records",
        null=True,
        blank=True,
        verbose_name="Dosen yang memfinalisasi"
    )

    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Waktu finalisasi"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Tanggal dibuat"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"],
                name="unique_student_attendance_per_session"
            )
        ]
        ordering = ["student__username"]

    def __str__(self):
        return (
            f"{self.student.username} - "
            f"{self.session} - {self.get_status_display()}"
        )


class AttendanceChangeLog(models.Model):
    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.PROTECT,
        related_name="change_logs",
        verbose_name="Catatan presensi"
    )

    old_status = models.CharField(
        max_length=15,
        choices=AttendanceRecord.Status.choices,
        verbose_name="Status sebelumnya"
    )

    new_status = models.CharField(
        max_length=15,
        choices=AttendanceRecord.Status.choices,
        verbose_name="Status terbaru"
    )

    reason = models.TextField(
        verbose_name="Alasan perubahan"
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_changes",
        verbose_name="Pengubah status"
    )

    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Waktu perubahan"
    )

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return (
            f"{self.attendance_record.student.username}: "
            f"{self.get_old_status_display()} → "
            f"{self.get_new_status_display()}"
        )
