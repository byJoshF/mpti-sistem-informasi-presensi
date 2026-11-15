
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.models import User
from attendance.models import AttendanceSession
from classrooms.models import Classroom, Enrollment


@login_required
def home(request):
    """
    Mengarahkan pengguna ke beranda sesuai perannya.
    """

    if request.user.is_superuser:
        return redirect("admin:index")

    now = timezone.now()

    # BERANDA MAHASISWA
    if request.user.role == User.Role.STUDENT:

        active_sessions = AttendanceSession.objects.filter(
            classroom_id=OuterRef("classroom_id"),
            status=AttendanceSession.Status.OPEN,
            expires_at__gt=now
        )

        enrollments = list(
            Enrollment.objects
            .filter(
                student=request.user,
                is_active=True
            )
            .select_related(
                "classroom",
                "classroom__teacher"
            )
            .annotate(
                has_active_session=Exists(active_sessions)
            )
            .order_by(
                "-has_active_session",
                "-joined_at"
            )
        )

        active_session_count = sum(
            1 for enrollment in enrollments
            if enrollment.has_active_session
        )

        context = {
            "enrollments": enrollments,
            "class_count": len(enrollments),
            "active_session_count": active_session_count,
        }

        return render(
            request,
            "dashboard/student_dashboard.html",
            context
        )

    # BERANDA DOSEN
    if request.user.role == User.Role.TEACHER:

        active_sessions = AttendanceSession.objects.filter(
            classroom_id=OuterRef("pk"),
            status=AttendanceSession.Status.OPEN,
            expires_at__gt=now
        )

        classrooms = list(
            Classroom.objects
            .filter(teacher=request.user)
            .annotate(
                active_student_count=Count(
                    "enrollments",
                    filter=Q(enrollments__is_active=True),
                    distinct=True
                ),
                has_active_session=Exists(active_sessions)
            )
            .order_by("-created_at")
        )

        total_students = sum(
            classroom.active_student_count
            for classroom in classrooms
        )

        active_session_count = sum(
            1 for classroom in classrooms
            if classroom.has_active_session
        )

        context = {
            "classrooms": classrooms,
            "class_count": len(classrooms),
            "total_students": total_students,
            "active_session_count": active_session_count,
        }

        return render(
            request,
            "dashboard/teacher_dashboard.html",
            context
        )

    raise PermissionDenied(
        "Peran pengguna tidak dikenali."
    )
