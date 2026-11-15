
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from classrooms.models import Enrollment

from .models import AttendanceRecord, AttendanceSession


@login_required
def student_history_list(request):
    """
    Menampilkan seluruh kelas yang pernah diikuti mahasiswa,
    termasuk kelas yang sudah ditinggalkan.
    """
    if request.user.role != "STUDENT":
        raise PermissionDenied

    enrollments = (
        Enrollment.objects
        .filter(student=request.user)
        .select_related(
            "classroom",
            "classroom__teacher"
        )
        .order_by("-is_active", "-joined_at")
    )

    return render(
        request,
        "attendance/student_history_list.html",
        {
            "enrollments": enrollments,
        }
    )


@login_required
def student_class_history(request, classroom_id):
    """
    Menampilkan riwayat presensi mahasiswa pada satu kelas.
    """
    if request.user.role != "STUDENT":
        raise PermissionDenied

    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            "classroom",
            "classroom__teacher"
        ),
        classroom_id=classroom_id,
        student=request.user
    )

    # Semua sesi resmi ditampilkan, kecuali sesi yang dibatalkan.
    sessions = list(
        AttendanceSession.objects
        .filter(classroom=enrollment.classroom)
        .exclude(status=AttendanceSession.Status.CANCELLED)
        .order_by("meeting_number")
    )

    # Mengambil catatan presensi milik mahasiswa untuk kelas tersebut.
    records = (
        AttendanceRecord.objects
        .filter(
            student=request.user,
            session__classroom=enrollment.classroom
        )
        .exclude(
            session__status=AttendanceSession.Status.CANCELLED
        )
        .select_related("session")
    )

    records_by_session = {
        record.session_id: record
        for record in records
    }

    # Menyiapkan penghitung setiap status.
    status_counts = {
        status: 0
        for status, label in AttendanceRecord.Status.choices
    }

    history_rows = []

    for session in sessions:
        record = records_by_session.get(session.id)

        if record:
            status = record.status
            submitted_at = record.submitted_at
        else:
            # Jika catatan belum tersedia, tampilkan sebagai
            # Belum Mengisi tanpa mengubah database.
            status = AttendanceRecord.Status.NOT_SUBMITTED
            submitted_at = None

        status_counts[status] += 1

        history_rows.append({
            "session": session,
            "status": status,
            "status_label": dict(
                AttendanceRecord.Status.choices
            ).get(status, status),
            "submitted_at": submitted_at,
        })

    total_sessions = len(sessions)

    present_count = status_counts[
        AttendanceRecord.Status.PRESENT
    ]

    permitted_count = status_counts[
        AttendanceRecord.Status.PERMITTED
    ]

    sick_count = status_counts[
        AttendanceRecord.Status.SICK
    ]

    absent_count = status_counts[
        AttendanceRecord.Status.ABSENT
    ]

    not_submitted_count = status_counts[
        AttendanceRecord.Status.NOT_SUBMITTED
    ]

    attendance_percentage = (
        round((present_count / total_sessions) * 100, 1)
        if total_sessions > 0
        else 0
    )

    context = {
        "enrollment": enrollment,
        "history_rows": history_rows,

        "total_sessions": total_sessions,

        "present_count": present_count,
        "permitted_count": permitted_count,
        "sick_count": sick_count,
        "absent_count": absent_count,
        "not_submitted_count": not_submitted_count,

        "attendance_percentage": attendance_percentage,

        "has_pending": not_submitted_count > 0,
    }

    return render(
        request,
        "attendance/student_class_history.html",
        context
    )
