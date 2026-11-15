from django.db import migrations, models


def restore_final_sessions(apps, schema_editor):
    """
    Mengubah sesi percobaan yang sebelumnya berstatus FINAL
    menjadi EXPIRED agar dosen dapat mengelolanya kembali.
    Catatan presensi tidak dihapus.
    """
    AttendanceSession = apps.get_model(
        "attendance",
        "AttendanceSession"
    )

    database = schema_editor.connection.alias

    AttendanceSession.objects.using(database).filter(
        status="FINAL"
    ).update(
        status="EXPIRED"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            restore_final_sessions,
            migrations.RunPython.noop
        ),

        migrations.AlterField(
            model_name="attendancesession",
            name="status",
            field=models.CharField(
                choices=[
                    ("OPEN", "Terbuka"),
                    ("CLOSED", "Ditutup"),
                    ("EXPIRED", "Kedaluwarsa"),
                    ("CANCELLED", "Dibatalkan"),
                ],
                default="OPEN",
                max_length=12,
                verbose_name="Status sesi"
            ),
        ),

        migrations.RemoveField(
            model_name="attendancerecord",
            name="finalized_at",
        ),

        migrations.RemoveField(
            model_name="attendancerecord",
            name="finalized_by",
        ),
    ]