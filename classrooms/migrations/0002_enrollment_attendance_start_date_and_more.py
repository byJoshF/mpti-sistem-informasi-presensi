import django.utils.timezone
from django.db import migrations, models


def backfill_attendance_start_date(apps, schema_editor):
    Enrollment = apps.get_model("classrooms", "Enrollment")
    database = schema_editor.connection.alias

    enrollments = Enrollment.objects.using(database).all()

    for enrollment in enrollments.iterator():
        start_date = django.utils.timezone.localdate(
            enrollment.joined_at
        )

        Enrollment.objects.using(database).filter(
            pk=enrollment.pk
        ).update(
            attendance_start_date=start_date
        )


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="attendance_start_date",
            field=models.DateField(
                default=django.utils.timezone.localdate,
                verbose_name="Tanggal mulai perhitungan presensi"
            ),
        ),
        migrations.RunPython(
            backfill_attendance_start_date,
            migrations.RunPython.noop
        ),
    ]