
from datetime import datetime, time, timedelta
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import User
from classrooms.models import Classroom, Enrollment, EnrollmentPeriod
from attendance.models import (
    AttendanceSession,
    AttendanceRecord,
    AttendanceChangeLog,
)


# IDENTITAS DEMO TETAP

DEMO_STUDENTS = [
    ("2601102384", "Aditya Pratama Wicaksono"),
    ("2601105172", "Nabila Putri Ramadhani"),
    ("2601106943", "Rizky Maulana Saputra"),
    ("2601201538", "Salsabila Nur Aini"),
    ("2601204871", "Fajar Ramadhan"),
    ("2601209265", "Dinda Ayu Maharani"),
    ("2601302749", "Muhammad Rafi Pratama"),
    ("2601306815", "Nadia Safitri"),
    ("2601403927", "Bima Arya Nugraha"),
    ("2601408156", "Putri Amelia"),
    ("2601502473", "Daffa Alfarizi"),
    ("2601506391", "Intan Permata Sari"),
    ("2601501845", "Rangga Firmansyah"),
    ("2601605729", "Aulia Rahmawati"),
    ("2601703168", "Kevin Alexander"),
    ("2601708452", "Citra Lestari"),
    ("2601802396", "Ilham Akbar"),
    ("2601806741", "Natasya Kirana"),
    ("2601904285", "Farhan Hidayat"),
    ("2601907536", "Melati Puspitasari"),
]


DEMO_CLASSROOMS = [
    {
        "name": "Pemrograman Web",
        "description": (
            "Kelas demonstrasi SIHADIR. "
            "Digunakan untuk memperlihatkan sesi presensi aktif "
            "dan mahasiswa yang sudah maupun belum mengisi."
        ),
    },
    {
        "name": "Basis Data",
        "description": (
            "Kelas demonstrasi SIHADIR. "
            "Digunakan untuk memperlihatkan riwayat pertemuan, "
            "variasi status, pembatalan sesi, dan rekap lengkap."
        ),
    },
    {
        "name": "Manajemen Proyek TI",
        "description": (
            "Kelas demonstrasi SIHADIR. "
            "Digunakan untuk memperlihatkan status belum mengisi, "
            "mahasiswa keluar, dan bergabung kembali."
        ),
    },
]


STATUS_PATTERN = (
    [AttendanceRecord.Status.PRESENT] * 10
    + [AttendanceRecord.Status.PERMITTED] * 3
    + [AttendanceRecord.Status.SICK] * 2
    + [AttendanceRecord.Status.ABSENT] * 5
)


# PERINTAH UTAMA

class Command(BaseCommand):

    help = (
        "Membuat, mereset, atau menghapus data demonstrasi SIHADIR "
        "khusus pada Neon Staging."
    )

    def add_arguments(self, parser):

        group = parser.add_mutually_exclusive_group()

        group.add_argument(
            "--reset",
            action="store_true",
            help="Hapus dan buat ulang data kelas demonstrasi."
        )

        group.add_argument(
            "--delete",
            action="store_true",
            help="Hapus data kelas demonstrasi, tetapi pertahankan akun."
        )

        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Konfirmasi tindakan reset atau penghapusan."
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Periksa koneksi dan tindakan tanpa mengubah database."
        )

    def handle(self, *args, **options):

        self.check_staging_database()

        reset = options["reset"]
        delete = options["delete"]
        confirm = options["confirm"]
        dry_run = options["dry_run"]

        if (reset or delete) and not confirm:
            raise CommandError(
                "Tindakan reset atau delete memerlukan --confirm."
            )

        if dry_run:

            self.stdout.write(
                self.style.SUCCESS(
                    "Koneksi Neon Staging berhasil dikenali."
                )
            )

            self.stdout.write(
                "Database: {}".format(
                    connection.settings_dict.get("NAME")
                )
            )

            if delete:
                self.stdout.write(
                    "Mode: simulasi penghapusan kelas dan presensi demo."
                )
            elif reset:
                self.stdout.write(
                    "Mode: simulasi reset dan pembuatan ulang data demo."
                )
            else:
                self.stdout.write(
                    "Mode: simulasi pembuatan data demo."
                )

            self.stdout.write(
                "Tidak ada data database yang diubah."
            )

            return

        with transaction.atomic():

            if reset or delete:

                deleted_count = self.remove_demo_classrooms()

                self.stdout.write(
                    f"Kelas demo lama yang dihapus: {deleted_count}"
                )

            if delete:

                self.stdout.write(
                    self.style.SUCCESS(
                        "Data kelas dan presensi demo berhasil dihapus."
                    )
                )

                self.stdout.write(
                    "Akun dosen dan mahasiswa demo tetap dipertahankan."
                )

                return

            elif Classroom.objects.filter(is_demo=True).exists():

                raise CommandError(
                    "Data demo sudah tersedia. "
                    "Gunakan --reset --confirm untuk membuat ulang."
                )

            teacher_password = os.getenv(
                "DEMO_TEACHER_PASSWORD",
                ""
            )

            student_password = os.getenv(
                "DEMO_STUDENT_PASSWORD",
                ""
            )

            if not teacher_password or not student_password:
                raise CommandError(
                    "DEMO_TEACHER_PASSWORD dan DEMO_STUDENT_PASSWORD "
                    "wajib diisi pada .env.staging."
                )

            teacher = self.ensure_demo_user(
                username="dosen.demo",
                full_name="Dosen Demonstrasi SIHADIR",
                email="dosen.demo@sihadir.test",
                role=User.Role.TEACHER,
                password=teacher_password,
            )

            students = []

            for nim, full_name in DEMO_STUDENTS:

                student = self.ensure_demo_user(
                    username=nim,
                    full_name=full_name,
                    email=f"{nim}@sihadir.test",
                    role=User.Role.STUDENT,
                    password=student_password,
                )

                students.append(student)

            self.create_demo_dataset(teacher, students)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "DATA DEMO SIHADIR BERHASIL DIBUAT."
            )
        )

        self.stdout.write("Akun dosen: dosen.demo")
        self.stdout.write("Jumlah mahasiswa: 20")
        self.stdout.write("Jumlah kelas: 3")
        self.stdout.write("Jumlah keanggotaan: 60")

        self.stdout.write("")
        self.stdout.write(
            "Password akun ditetapkan dari variabel "
            "DEMO_TEACHER_PASSWORD dan DEMO_STUDENT_PASSWORD."
        )

        self.stdout.write(
            "Sesi aktif dibuat pada kelas Pemrograman Web."
        )


    # PERLINDUNGAN DATABASE

    def check_staging_database(self):

        if getattr(settings, "DEMO_DATA_ENV", "") != "staging":
            raise CommandError(
                "Perintah ini hanya boleh dijalankan menggunakan "
                "config.settings_staging."
            )

        if connection.vendor != "postgresql":
            raise CommandError(
                "Database yang digunakan bukan PostgreSQL."
            )

        host = (
            connection.settings_dict.get("HOST", "")
            .lower()
        )

        if "neon.tech" not in host:
            raise CommandError(
                "Database bukan berasal dari host Neon."
            )

        if "-pooler" in host:
            raise CommandError(
                "Gunakan koneksi Direct Neon, bukan koneksi pooled."
            )


    # AKUN DEMONSTRASI

    def ensure_demo_user(
        self,
        username,
        full_name,
        email,
        role,
        password
    ):

        email_owner = User.objects.filter(
            email__iexact=email
        ).first()

        if (
            email_owner
            and email_owner.username != username
        ):
            raise CommandError(
                f"Email demo {email} sudah digunakan akun lain."
            )

        user = User.objects.filter(
            username=username
        ).first()

        if user:

            if not user.is_demo:
                raise CommandError(
                    f"Username {username} sudah digunakan akun "
                    "yang bukan akun demo. Demi keamanan, akun "
                    "tersebut tidak akan diubah."
                )

            if user.is_superuser:
                raise CommandError(
                    f"Akun {username} merupakan superuser. "
                    "Tidak boleh digunakan sebagai akun demo."
                )

            if user.role != role:
                raise CommandError(
                    f"Role akun {username} tidak sesuai."
                )

        else:

            user = User(
                username=username,
                is_demo=True,
            )

        user.full_name = full_name
        user.email = email
        user.role = role
        user.is_demo = True
        user.is_staff = False
        user.set_password(password)

        user.save()

        return user


    # PENGHAPUSAN DATA DEMO

    def remove_demo_classrooms(self):

        demo_classrooms = Classroom.objects.filter(
            is_demo=True
        )

        classroom_count = demo_classrooms.count()

        if not classroom_count:
            return 0

        # Hapus log terlebih dahulu karena menggunakan PROTECT.
        AttendanceChangeLog.objects.filter(
            attendance_record__session__classroom__is_demo=True
        ).delete()

        # Catatan presensi harus dihapus sebelum sesi.
        AttendanceRecord.objects.filter(
            session__classroom__is_demo=True
        ).delete()

        # Sesi menggunakan PROTECT terhadap kelas.
        AttendanceSession.objects.filter(
            classroom__in=demo_classrooms
        ).delete()

        # Enrollment dan EnrollmentPeriod akan terhapus
        # melalui relasi CASCADE saat kelas dihapus.
        demo_classrooms.delete()

        return classroom_count


    # WAKTU DEMONSTRASI

    def days_ago(self, days, hour=9):

        local_date = (
            timezone.localdate()
            - timedelta(days=days)
        )

        naive_datetime = datetime.combine(
            local_date,
            time(hour, 0)
        )

        return timezone.make_aware(
            naive_datetime,
            timezone.get_current_timezone()
        )


    # MEMBUAT KELAS

    def create_demo_classroom(self, teacher, data):

        return Classroom.objects.create(
            teacher=teacher,
            name=data["name"],
            description=data["description"],
            is_demo=True,
        )


    # MEMBUAT ENROLLMENT DAN PERIODE

    def create_enrollment(
        self,
        classroom,
        student,
        period_specs
    ):

        latest_joined_at = period_specs[-1][0]

        active = period_specs[-1][1] is None

        enrollment = Enrollment.objects.create(
            classroom=classroom,
            student=student,
            is_active=active,
        )

        # joined_at pada Enrollment menggunakan auto_now_add.
        # Atur tanggal riwayat awal sesuai periode demo.
        Enrollment.objects.filter(
            pk=enrollment.pk
        ).update(
            joined_at=period_specs[0][0]
        )

        for joined_at, left_at in period_specs:

            EnrollmentPeriod.objects.create(
                enrollment=enrollment,
                joined_at=joined_at,
                left_at=left_at,
                is_active=(left_at is None),
            )

        return enrollment


    # MEMBUAT SESI

    def create_session(
        self,
        classroom,
        started_at,
        duration_minutes=15,
        status=AttendanceSession.Status.EXPIRED,
        cancellation_reason=""
    ):

        session = AttendanceSession.objects.create(
            classroom=classroom,
            duration_minutes=duration_minutes,
            started_at=started_at,
            status=status,
            cancellation_reason=cancellation_reason,
        )

        if status != AttendanceSession.Status.OPEN:

            session.closed_at = session.expires_at

            session.save(
                update_fields=["closed_at"]
            )

        return session


    # POLA STATUS PRESENSI

    def patterned_status(self, student_index, session_index):

        return STATUS_PATTERN[
            (student_index + session_index * 3)
            % len(STATUS_PATTERN)
        ]


    # MEMBUAT RECORD PRESENSI

    def create_session_records(
        self,
        session,
        students,
        session_index,
        scenario,
        days_ago_value=None
    ):

        records = {}

        for student_index, student in enumerate(students):

            status = self.patterned_status(
                student_index,
                session_index
            )

            if scenario == "active":

                status = (
                    AttendanceRecord.Status.PRESENT
                    if student_index < 12
                    else AttendanceRecord.Status.NOT_SUBMITTED
                )

            elif scenario == "rejoin":

                # Mahasiswa nomor 19 keluar 10 hari lalu.
                # Dua sesi setelah keluar belum diselesaikan.
                if (
                    student_index == 18
                    and days_ago_value is not None
                    and days_ago_value <= 10
                ):
                    status = AttendanceRecord.Status.NOT_SUBMITTED

                # Mahasiswa nomor 20 bergabung kembali 5 hari lalu.
                # Sesi 7 hari lalu terjadi pada masa jeda.
                if (
                    student_index == 19
                    and days_ago_value == 7
                ):
                    status = AttendanceRecord.Status.NOT_SUBMITTED

            submitted_at = None

            if status == AttendanceRecord.Status.PRESENT:
                submitted_at = (
                    session.started_at
                    + timedelta(minutes=2)
                )

            record = AttendanceRecord.objects.create(
                session=session,
                student=student,
                status=status,
                submitted_at=submitted_at,
            )

            records[student.username] = record

        return records


    # RIWAYAT PERUBAHAN STATUS

    def create_demo_change_log(
        self,
        record,
        teacher,
        old_status,
        new_status,
        reason
    ):

        record.status = new_status

        record.save(
            update_fields=["status"]
        )

        AttendanceChangeLog.objects.create(
            attendance_record=record,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=teacher,
        )


    # MEMBUAT SELURUH DATA DEMO

    def create_demo_dataset(self, teacher, students):

        # KELAS 1: PEMROGRAMAN WEB

        class1 = self.create_demo_classroom(
            teacher,
            DEMO_CLASSROOMS[0]
        )

        initial_join = self.days_ago(30, 8)

        for student in students:

            self.create_enrollment(
                class1,
                student,
                [
                    (initial_join, None)
                ]
            )

        class1_sessions = []

        for index, days in enumerate([21, 14, 7]):

            session = self.create_session(
                class1,
                self.days_ago(days, 9),
            )

            self.create_session_records(
                session,
                students,
                index,
                "normal",
            )

            class1_sessions.append(session)

        active_session = self.create_session(
            class1,
            timezone.now() - timedelta(minutes=2),
            duration_minutes=30,
            status=AttendanceSession.Status.OPEN,
        )

        self.create_session_records(
            active_session,
            students,
            3,
            "active",
        )

        # KELAS 2: BASIS DATA

        class2 = self.create_demo_classroom(
            teacher,
            DEMO_CLASSROOMS[1]
        )

        class2_enrollments = {}

        for student in students:

            class2_enrollments[student.username] = (
                self.create_enrollment(
                    class2,
                    student,
                    [
                        (initial_join, None)
                    ]
                )
            )

        class2_sessions = []

        for index, days in enumerate([28, 21, 14, 7, 2]):

            session = self.create_session(
                class2,
                self.days_ago(days, 9),
            )

            records = self.create_session_records(
                session,
                students,
                index,
                "normal",
            )

            class2_sessions.append(records)

        # Tiga contoh riwayat perubahan status.
        self.create_demo_change_log(
            record=class2_sessions[1][students[2].username],
            teacher=teacher,
            old_status=AttendanceRecord.Status.NOT_SUBMITTED,
            new_status=AttendanceRecord.Status.PERMITTED,
            reason="Surat izin telah dikonfirmasi dosen.",
        )

        self.create_demo_change_log(
            record=class2_sessions[2][students[5].username],
            teacher=teacher,
            old_status=AttendanceRecord.Status.ABSENT,
            new_status=AttendanceRecord.Status.PRESENT,
            reason="Kehadiran dikoreksi berdasarkan bukti.",
        )

        self.create_demo_change_log(
            record=class2_sessions[3][students[8].username],
            teacher=teacher,
            old_status=AttendanceRecord.Status.NOT_SUBMITTED,
            new_status=AttendanceRecord.Status.SICK,
            reason="Surat keterangan sakit telah diterima.",
        )

        self.create_session(
            class2,
            self.days_ago(1, 9),
            status=AttendanceSession.Status.CANCELLED,
            cancellation_reason=(
                "Perkuliahan dibatalkan karena dosen berhalangan hadir."
            ),
        )

        # KELAS 3: MANAJEMEN PROYEK TI

        class3 = self.create_demo_classroom(
            teacher,
            DEMO_CLASSROOMS[2]
        )

        class3_join = self.days_ago(30, 8)
        class3_leave_19 = self.days_ago(10, 14)

        class3_rejoin_20 = self.days_ago(5, 8)
        class3_leave_20 = self.days_ago(12, 14)

        for student_index, student in enumerate(students):

            if student_index == 18:

                # Mahasiswa 19 sudah keluar dan belum bergabung lagi.
                period_specs = [
                    (
                        class3_join,
                        class3_leave_19
                    )
                ]

            elif student_index == 19:

                # Mahasiswa 20 keluar, lalu bergabung kembali.
                period_specs = [
                    (
                        class3_join,
                        class3_leave_20
                    ),
                    (
                        class3_rejoin_20,
                        None
                    )
                ]

            else:

                period_specs = [
                    (
                        class3_join,
                        None
                    )
                ]

            self.create_enrollment(
                class3,
                student,
                period_specs
            )

        for index, days in enumerate([28, 21, 14, 7, 2]):

            session = self.create_session(
                class3,
                self.days_ago(days, 9),
            )

            self.create_session_records(
                session,
                students,
                index,
                "rejoin",
                days_ago_value=days,
            )

        self.create_session(
            class3,
            self.days_ago(1, 9),
            status=AttendanceSession.Status.CANCELLED,
            cancellation_reason=(
                "Jadwal kuliah dipindahkan oleh dosen."
            ),
        )

        # RINGKASAN

        self.stdout.write(
            f"Kelas dibuat: {class1.name}"
        )

        self.stdout.write(
            f"Kode gabung: {class1.join_code}"
        )

        self.stdout.write(
            f"Sesi aktif: Pertemuan {active_session.meeting_number}"
        )

        self.stdout.write(
            f"Kelas dibuat: {class2.name}"
        )

        self.stdout.write(
            f"Kode gabung: {class2.join_code}"
        )

        self.stdout.write(
            f"Kelas dibuat: {class3.name}"
        )

        self.stdout.write(
            f"Kode gabung: {class3.join_code}"
        )
