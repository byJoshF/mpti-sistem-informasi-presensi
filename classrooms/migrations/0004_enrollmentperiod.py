from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def copy_existing_enrollments(apps, schema_editor):
    Enrollment = apps.get_model("classrooms", "Enrollment")
    EnrollmentPeriod = apps.get_model(
        "classrooms",
        "EnrollmentPeriod"
    )

    database = schema_editor.connection.alias
    batch = []

    enrollments = Enrollment.objects.using(database).all().iterator()

    for enrollment in enrollments:
        batch.append(
            EnrollmentPeriod(
                enrollment_id=enrollment.pk,
                joined_at=enrollment.joined_at,
                attendance_start_date=enrollment.attendance_start_date,
                is_active=enrollment.is_active,
                left_at=None
            )
        )

        if len(batch) >= 500:
            EnrollmentPeriod.objects.using(database).bulk_create(batch)
            batch = []

    if batch:
        EnrollmentPeriod.objects.using(database).bulk_create(batch)


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0003_alter_enrollment_joined_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnrollmentPeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID"
                    )
                ),
                (
                    "joined_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="Waktu mulai bergabung"
                    )
                ),
                (
                    "left_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Waktu keluar dari kelas"
                    )
                ),
                (
                    "attendance_start_date",
                    models.DateField(
                        default=django.utils.timezone.localdate,
                        verbose_name="Tanggal mulai perhitungan presensi"
                    )
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        verbose_name="Periode aktif"
                    )
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Tanggal pencatatan"
                    )
                ),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="periods",
                        to="classrooms.enrollment",
                        verbose_name="Keanggotaan"
                    )
                ),
            ],
            options={
                "ordering": ["-joined_at"],
            },
        ),

        migrations.RunPython(
            copy_existing_enrollments,
            migrations.RunPython.noop
        ),

        migrations.AddConstraint(
            model_name="enrollmentperiod",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("enrollment",),
                name="one_active_period_per_enrollment"
            ),
        ),
    ]