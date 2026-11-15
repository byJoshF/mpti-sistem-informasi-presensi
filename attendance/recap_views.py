from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from classrooms.models import Classroom, Enrollment

from .forms import AttendanceRecapForm
from .models import AttendanceSession, AttendanceRecord


@login_required
def semester_recap(request, classroom_id):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk dosen."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    # Kedaluwarsakan sesi yang waktunya sudah habis.
    now = timezone.now()

    AttendanceSession.objects.filter(
        classroom=classroom,
        status=AttendanceSession.Status.OPEN,
        expires_at__lte=now
    ).update(
        status=AttendanceSession.Status.EXPIRED,
        closed_at=now
    )

    form = AttendanceRecapForm(
        request.POST or None
    )

    context = {
        "classroom": classroom,
        "form": form,
        "report_generated": False,
        "report_ready": False,
        "no_sessions": False,
        "pending_count": 0,
        "active_sessions": [],
        "pending_records": [],
        "student_results": [],
    }

    if request.method == "POST" and form.is_valid():

        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        sessions = list(
            AttendanceSession.objects.filter(
                classroom=classroom,
                started_at__date__gte=start_date,
                started_at__date__lte=end_date
            )
            .exclude(
                status=AttendanceSession.Status.CANCELLED
            )
            .order_by("meeting_number")
        )

        context.update({
            "report_generated": True,
            "start_date": start_date,
            "end_date": end_date,
            "total_sessions": len(sessions),
        })

        if not sessions:
            context["no_sessions"] = True

            return render(
                request,
                "attendance/semester_recap.html",
                context
            )

        enrollments = list(
            Enrollment.objects.filter(
                classroom=classroom
            ).select_related(
                "student"
            ).order_by(
                "student__username"
            )
        )
        context["student_count"] = len(enrollments)

        # Siapkan catatan untuk setiap mahasiswa pada setiap
        # sesi resmi dalam periode tersebut.
        #
        # Catatan yang sudah ada tidak diubah.
        # Ini juga menangani mahasiswa yang bergabung kembali
        # dan sesi yang terlewat ketika ia keluar.
        with transaction.atomic():
            batch = []

            for session in sessions:
                for enrollment in enrollments:
                    batch.append(
                        AttendanceRecord(
                            session=session,
                            student=enrollment.student
                        )
                    )

                    if len(batch) >= 500:
                        AttendanceRecord.objects.bulk_create(
                            batch,
                            ignore_conflicts=True
                        )
                        batch = []

            if batch:
                AttendanceRecord.objects.bulk_create(
                    batch,
                    ignore_conflicts=True
                )

        session_ids = [session.pk for session in sessions]

        pending_records = list(
            AttendanceRecord.objects.filter(
                session_id__in=session_ids,
                status=AttendanceRecord.Status.NOT_SUBMITTED
            ).select_related(
                "student",
                "session"
            ).order_by(
                "session__meeting_number",
                "student__username"
            )
        )

        active_sessions = [
            session
            for session in sessions
            if (
                session.status == AttendanceSession.Status.OPEN
                and session.expires_at > timezone.now()
            )
        ]

        pending_count = len(pending_records)

        report_ready = (
            pending_count == 0
            and len(active_sessions) == 0
        )

        context.update({
            "pending_count": pending_count,
            "pending_records": pending_records,
            "active_sessions": active_sessions,
            "report_ready": report_ready,
        })

        # Rekap hanya ditampilkan jika semua catatan sudah ditinjau
        # dan tidak ada sesi yang masih berlangsung.
        if report_ready:
            student_results = []

            for enrollment in enrollments:
                result = AttendanceRecord.objects.filter(
                    session_id__in=session_ids,
                    student=enrollment.student
                ).aggregate(
                    total_records=Count("id"),
                    present_count=Count(
                        "id",
                        filter=Q(
                            status=AttendanceRecord.Status.PRESENT
                        )
                    ),
                    permitted_count=Count(
                        "id",
                        filter=Q(
                            status=AttendanceRecord.Status.PERMITTED
                        )
                    ),
                    sick_count=Count(
                        "id",
                        filter=Q(
                            status=AttendanceRecord.Status.SICK
                        )
                    ),
                    absent_count=Count(
                        "id",
                        filter=Q(
                            status=AttendanceRecord.Status.ABSENT
                        )
                    ),
                )

                present_count = result["present_count"]

                percentage = round(
                    (present_count / len(sessions)) * 100,
                    1
                )

                student_results.append({
                    "student": enrollment.student,
                    "enrollment": enrollment,
                    "present_count": present_count,
                    "permitted_count": result["permitted_count"],
                    "sick_count": result["sick_count"],
                    "absent_count": result["absent_count"],
                    "total_sessions": len(sessions),
                    "percentage": percentage,
                })

            student_results.sort(
                key=lambda item: (
                    -item["percentage"],
                    (item["student"].full_name or "").casefold(),
                    item["student"].username.casefold(),
                )
            )
            context["student_results"] = student_results

    return render(
        request,
        "attendance/semester_recap.html",
        context
    )