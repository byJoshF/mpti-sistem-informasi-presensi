from datetime import datetime, time, timedelta

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

    # Perbarui status sesi yang sudah melewati batas waktu.
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

        # Gunakan rentang datetime, bukan fungsi DATE pada kolom
        # started_at, agar query lebih efisien.
        start_datetime = timezone.make_aware(
            datetime.combine(
                start_date,
                time.min
            )
        )

        end_datetime = timezone.make_aware(
            datetime.combine(
                end_date + timedelta(days=1),
                time.min
            )
        )

        sessions = list(
            AttendanceSession.objects.filter(
                classroom=classroom,
                started_at__gte=start_datetime,
                started_at__lt=end_datetime
            )
            .exclude(
                status=AttendanceSession.Status.CANCELLED
            )
            .order_by("meeting_number")
        )

        session_ids = [
            session.pk
            for session in sessions
        ]

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
            )
            .select_related("student")
            .order_by("student__username")
        )

        context["student_count"] = len(enrollments)

        student_ids = [
            enrollment.student_id
            for enrollment in enrollments
        ]

        # Ambil seluruh pasangan sesi-mahasiswa yang sudah memiliki
        # catatan. Ini dilakukan sekali, bukan berulang kali.
        existing_pairs = set(
            AttendanceRecord.objects.filter(
                session_id__in=session_ids,
                student_id__in=student_ids
            ).values_list(
                "session_id",
                "student_id"
            )
        )

        # Buat hanya catatan yang benar-benar belum ada.
        # Catatan dan status yang sudah tersedia tidak ditimpa.
        with transaction.atomic():

            batch = []

            for session in sessions:

                for enrollment in enrollments:

                    pair = (
                        session.pk,
                        enrollment.student_id
                    )

                    if pair in existing_pairs:
                        continue

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


        # Ambil seluruh catatan yang masih perlu ditinjau.
        pending_records = list(
            AttendanceRecord.objects.filter(
                session_id__in=session_ids,
                status=AttendanceRecord.Status.NOT_SUBMITTED
            )
            .select_related(
                "student",
                "session"
            )
            .order_by(
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

        # Rekap hanya ditampilkan jika seluruh catatan sudah
        # ditinjau dan tidak ada sesi yang masih berlangsung.
        if report_ready:

            # Hitung seluruh status mahasiswa dalam satu query.
            # Ini menggantikan query agregasi di dalam loop.
            summary_rows = (
                AttendanceRecord.objects
                .filter(
                    session_id__in=session_ids
                )
                .order_by()
                .values("student_id")
                .annotate(
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
            )

            summary_by_student = {
                row["student_id"]: row
                for row in summary_rows
            }

            student_results = []

            for enrollment in enrollments:

                result = summary_by_student.get(
                    enrollment.student_id,
                    {
                        "present_count": 0,
                        "permitted_count": 0,
                        "sick_count": 0,
                        "absent_count": 0,
                    }
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

            # Persentase tertinggi di atas.
            # Jika persentase sama, urutkan nama alfabetis.
            student_results.sort(
                key=lambda item: (
                    -item["percentage"],
                    (
                        item["student"].full_name or ""
                    ).casefold(),
                    item["student"].username.casefold(),
                )
            )

            context["student_results"] = student_results

    return render(
        request,
        "attendance/semester_recap.html",
        context
    )