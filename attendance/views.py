from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import (
    Count,
    Case,
    When,
    Value,
    IntegerField,
    Q,
)
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from classrooms.models import Classroom, Enrollment

from .forms import (
    AttendanceSessionCreateForm,
    AttendanceSessionCancelForm,
    AttendanceCodeForm,
    AttendanceRecordStatusForm,
)

from .models import (
    AttendanceSession,
    AttendanceRecord,
    AttendanceChangeLog,
)


def expire_due_sessions(classroom):
    """Mengubah sesi terbuka yang waktunya habis menjadi kedaluwarsa."""
    now = timezone.now()

    AttendanceSession.objects.filter(
        classroom=classroom,
        status=AttendanceSession.Status.OPEN,
        expires_at__lte=now
    ).update(
        status=AttendanceSession.Status.EXPIRED,
        closed_at=now
    )


def render_session_list(request, classroom, form=None):
    """Menyiapkan daftar sesi beserta kondisi kelengkapan presensi."""

    sessions = (
        AttendanceSession.objects
        .filter(classroom=classroom)
        .annotate(
            total_records=Count(
                "attendance_records",
                distinct=True
            ),
            pending_records=Count(
                "attendance_records",
                filter=Q(
                    attendance_records__status=(
                        AttendanceRecord.Status.NOT_SUBMITTED
                    )
                ),
                distinct=True
            )
        )
        .order_by("-meeting_number")
    )

    now = timezone.now()

    for session in sessions:
        if session.status == AttendanceSession.Status.CANCELLED:
            session.display_state = "cancelled"
            session.display_state_label = "Dibatalkan"

        elif (
            session.status == AttendanceSession.Status.OPEN
            and session.expires_at > now
        ):
            session.display_state = "ongoing"
            session.display_state_label = "Sedang Berlangsung"

        elif (
            session.total_records > 0
            and session.pending_records == 0
        ):
            session.display_state = "complete"
            session.display_state_label = "Semua Status Terisi"

        else:
            session.display_state = "incomplete"
            session.display_state_label = "Belum Lengkap"

    active_session = next(
        (
            session
            for session in sessions
            if session.status == AttendanceSession.Status.OPEN
        ),
        None
    )

    return render(
        request,
        "attendance/session_list.html",
        {
            "classroom": classroom,
            "sessions": sessions,
            "active_session": active_session,
            "form": form or AttendanceSessionCreateForm(),
        }
    )


@login_required
def session_list(request, classroom_id):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk dosen."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    expire_due_sessions(classroom)

    return render_session_list(request, classroom)


@login_required
def session_create(request, classroom_id):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat membuat sesi absensi."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    form = AttendanceSessionCreateForm(request.POST)

    if not form.is_valid():
        expire_due_sessions(classroom)
        return render_session_list(request, classroom, form)

    with transaction.atomic():
        classroom = get_object_or_404(
            Classroom.objects.select_for_update(),
            pk=classroom_id,
            teacher=request.user
        )

        expire_due_sessions(classroom)

        active_session_exists = AttendanceSession.objects.filter(
            classroom=classroom,
            status=AttendanceSession.Status.OPEN
        ).exists()

        if active_session_exists:
            messages.warning(
                request,
                "Masih ada sesi absensi yang aktif di kelas ini."
            )

        else:
            session = AttendanceSession.objects.create(
                classroom=classroom,
                duration_minutes=form.cleaned_data["duration_minutes"]
            )

            student_ids = Enrollment.objects.filter(
                classroom=classroom,
                is_active=True
            ).values_list(
                "student_id",
                flat=True
            )

            AttendanceRecord.objects.bulk_create(
                [
                    AttendanceRecord(
                        session=session,
                        student_id=student_id
                    )
                    for student_id in student_ids
                ],
                ignore_conflicts=True
            )

            messages.success(
                request,
                f"Sesi absensi pertemuan {session.meeting_number} "
                "berhasil dibuat."
            )

    return redirect(
        "attendance:session_list",
        classroom_id=classroom.pk
    )


@login_required
@require_POST
def session_cancel(request, classroom_id, session_id):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat membatalkan sesi."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    expire_due_sessions(classroom)

    with transaction.atomic():
        session = get_object_or_404(
            AttendanceSession.objects.select_for_update(),
            pk=session_id,
            classroom=classroom
        )

        if session.status not in [
            AttendanceSession.Status.OPEN,
            AttendanceSession.Status.EXPIRED,
        ]:
            messages.error(
                request,
                "Sesi ini tidak dapat dibatalkan."
            )

            return redirect(
                "attendance:session_list",
                classroom_id=classroom.pk
            )

        form = AttendanceSessionCancelForm(request.POST)

        if form.is_valid():
            session.status = AttendanceSession.Status.CANCELLED
            session.closed_at = timezone.now()
            session.cancellation_reason = form.cleaned_data["reason"]

            session.save(update_fields=[
                "status",
                "closed_at",
                "cancellation_reason"
            ])

            messages.success(
                request,
                "Sesi absensi berhasil dibatalkan. Riwayat tetap disimpan."
            )

        else:
            messages.error(
                request,
                "Alasan pembatalan wajib diisi minimal 5 karakter."
            )

    return redirect(
        "attendance:session_list",
        classroom_id=classroom.pk
    )


@login_required
def student_submit_attendance(request, classroom_id):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden(
            "Hanya mahasiswa yang dapat mengisi presensi."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id
    )

    enrollment = Enrollment.objects.filter(
        classroom=classroom,
        student=request.user,
        is_active=True
    ).first()

    if not enrollment:
        return HttpResponseForbidden(
            "Kamu tidak terdaftar sebagai mahasiswa aktif di kelas ini."
        )

    attempts_key = f"attendance_attempts_user_{request.user.pk}"
    attempts = cache.get(attempts_key, 0)

    if attempts >= 5:
        messages.error(
            request,
            "Terlalu banyak percobaan kode yang salah. "
            "Silakan coba kembali setelah 10 menit."
        )

        return render(
            request,
            "attendance/submit_attendance.html",
            {
                "classroom": classroom,
                "form": AttendanceCodeForm()
            }
        )

    if request.method == "POST":
        form = AttendanceCodeForm(request.POST)

        if form.is_valid():
            expire_due_sessions(classroom)

            code = form.cleaned_data["attendance_code"]

            with transaction.atomic():
                session = AttendanceSession.objects.select_for_update().filter(
                    classroom=classroom,
                    attendance_code=code,
                    status=AttendanceSession.Status.OPEN,
                    expires_at__gt=timezone.now()
                ).first()

                if not session:
                    current_attempts = cache.get(attempts_key, 0)

                    cache.set(
                        attempts_key,
                        current_attempts + 1,
                        timeout=600
                    )

                    messages.error(
                        request,
                        "Kode tidak sesuai, sesi belum aktif, "
                        "atau sudah kedaluwarsa."
                    )

                else:
                    record, created = AttendanceRecord.objects.get_or_create(
                        session=session,
                        student=request.user,
                        defaults={
                            "status": AttendanceRecord.Status.NOT_SUBMITTED
                        }
                    )

                    record = AttendanceRecord.objects.select_for_update().get(
                        pk=record.pk
                    )

                    if record.status == AttendanceRecord.Status.NOT_SUBMITTED:
                        record.status = AttendanceRecord.Status.PRESENT
                        record.submitted_at = timezone.now()

                        record.save(update_fields=[
                            "status",
                            "submitted_at"
                        ])

                        cache.delete(attempts_key)

                        messages.success(
                            request,
                            "Presensi berhasil dicatat. "
                            "Kamu dinyatakan Hadir."
                        )

                    else:
                        messages.info(
                            request,
                            "Presensi untuk sesi ini sudah tercatat."
                        )

            return redirect(
                "attendance:student_submit",
                classroom_id=classroom.pk
            )

    else:
        form = AttendanceCodeForm()

    return render(
        request,
        "attendance/submit_attendance.html",
        {
            "classroom": classroom,
            "form": form
        }
    )


@login_required
def session_detail(request, classroom_id, session_id):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk dosen."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    expire_due_sessions(classroom)

    session = get_object_or_404(
        AttendanceSession,
        pk=session_id,
        classroom=classroom
    )

    # Siapkan catatan bagi mahasiswa aktif sebagai pengaman jika
    # ada catatan yang belum terbentuk saat sesi dibuat.
    if session.status in [
        AttendanceSession.Status.OPEN,
        AttendanceSession.Status.EXPIRED,
        AttendanceSession.Status.CLOSED,
    ]:
        active_student_ids = Enrollment.objects.filter(
            classroom=classroom,
            is_active=True
        ).values_list(
            "student_id",
            flat=True
        )

        AttendanceRecord.objects.bulk_create(
            [
                AttendanceRecord(
                    session=session,
                    student_id=student_id
                )
                for student_id in active_student_ids
            ],
            ignore_conflicts=True
        )

    # Jangan menyaring berdasarkan keanggotaan aktif saat ini.
    # Catatan yang sudah ada tetap terlihat, termasuk catatan lama
    # dan sesi yang terlewat ketika mahasiswa keluar.
    all_records = (
        AttendanceRecord.objects
        .filter(
            session=session,
            student__class_enrollments__classroom=classroom
        )
        .select_related("student")
        .prefetch_related("change_logs__changed_by")
        .order_by(
            Case(
                When(
                    status=AttendanceRecord.Status.NOT_SUBMITTED,
                    then=Value(0)
                ),
                default=Value(1),
                output_field=IntegerField()
            ),
            "student__username"
        )
    )

    pending_records = all_records.filter(
        status=AttendanceRecord.Status.NOT_SUBMITTED
    )

    resolved_records = all_records.exclude(
        status=AttendanceRecord.Status.NOT_SUBMITTED
    )

    total_students = all_records.count()

    present_count = all_records.filter(
        status=AttendanceRecord.Status.PRESENT
    ).count()

    not_submitted_count = pending_records.count()

    permitted_count = all_records.filter(
        status=AttendanceRecord.Status.PERMITTED
    ).count()

    sick_count = all_records.filter(
        status=AttendanceRecord.Status.SICK
    ).count()

    absent_count = all_records.filter(
        status=AttendanceRecord.Status.ABSENT
    ).count()

    show_pending_only = request.GET.get("pending") == "1"

    can_edit_records = session.status in [
        AttendanceSession.Status.EXPIRED,
        AttendanceSession.Status.CLOSED,
    ]

    context = {
        "classroom": classroom,
        "session": session,
        "pending_records": pending_records,
        "resolved_records": resolved_records,
        "total_students": total_students,
        "present_count": present_count,
        "not_submitted_count": not_submitted_count,
        "permitted_count": permitted_count,
        "sick_count": sick_count,
        "absent_count": absent_count,
        "show_pending_only": show_pending_only,
        "can_edit_records": can_edit_records,
    }

    return render(
        request,
        "attendance/session_detail.html",
        context
    )


@login_required
@require_POST
def record_update_status(
    request,
    classroom_id,
    session_id,
    record_id
):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat mengubah status presensi."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    expire_due_sessions(classroom)

    form = AttendanceRecordStatusForm(request.POST)

    if not form.is_valid():
        messages.error(
            request,
            "Status atau alasan perubahan tidak valid. "
            "Alasan minimal harus 5 karakter."
        )

        return redirect(
            "attendance:session_detail",
            classroom_id=classroom.pk,
            session_id=session_id
        )

    with transaction.atomic():
        session = get_object_or_404(
            AttendanceSession.objects.select_for_update(),
            pk=session_id,
            classroom=classroom
        )

        if session.status not in [
            AttendanceSession.Status.EXPIRED,
            AttendanceSession.Status.CLOSED,
        ]:
            messages.error(
                request,
                "Status hanya dapat diubah setelah sesi berakhir "
                "dan selama sesi belum dibatalkan."
            )

            return redirect(
                "attendance:session_detail",
                classroom_id=classroom.pk,
                session_id=session.pk
            )

        record = get_object_or_404(
            AttendanceRecord.objects.select_for_update(),
            pk=record_id,
            session=session
        )

        old_status = record.status
        new_status = form.cleaned_data["status"]

        if old_status == new_status:
            messages.info(
                request,
                "Status mahasiswa tidak berubah. "
                "Tidak ada riwayat perubahan baru."
            )

        else:
            old_status_label = dict(
                AttendanceRecord.Status.choices
            ).get(old_status, old_status)

            new_status_label = dict(
                AttendanceRecord.Status.choices
            ).get(new_status, new_status)

            record.status = new_status
            record.save(update_fields=["status"])

            AttendanceChangeLog.objects.create(
                attendance_record=record,
                old_status=old_status,
                new_status=new_status,
                reason=form.cleaned_data["reason"],
                changed_by=request.user
            )

            messages.success(
                request,
                f"Status {record.student.full_name} berhasil diubah "
                f"dari {old_status_label} menjadi {new_status_label}."
            )

    return redirect(
        "attendance:session_detail",
        classroom_id=classroom.pk,
        session_id=session_id
    )