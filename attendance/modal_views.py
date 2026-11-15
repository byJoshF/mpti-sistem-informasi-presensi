
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

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

from .views import expire_due_sessions


# =========================================================
# HELPER AJAX
# =========================================================

def is_ajax_request(request):
    return (
        request.headers.get("x-requested-with")
        == "XMLHttpRequest"
    )


def ajax_success(message):
    return JsonResponse({
        "success": True,
        "message": message,
    })


def ajax_error(message, status=400):
    return JsonResponse(
        {
            "success": False,
            "message": message,
        },
        status=status
    )


def ajax_form_error(
    request,
    template_name,
    context,
    status=400
):
    html = render_to_string(
        template_name,
        context,
        request=request
    )

    return JsonResponse(
        {
            "success": False,
            "html": html,
        },
        status=status
    )


# =========================================================
# MEMBUAT SESI PRESENSI
# =========================================================

@login_required
@require_http_methods(["GET", "POST"])
def session_create(request, classroom_id):

    if request.user.role != "TEACHER":
        if is_ajax_request(request):
            return ajax_error(
                "Hanya dosen yang dapat membuat sesi.",
                status=403
            )

        return HttpResponseForbidden(
            "Hanya dosen yang dapat membuat sesi."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=classroom_id,
        teacher=request.user
    )

    if request.method == "GET":

        if request.GET.get("modal") == "1":
            return render(
                request,
                "attendance/partials/session_create_modal.html",
                {
                    "form": AttendanceSessionCreateForm(),
                    "action_url": request.path,
                    "classroom": classroom,
                }
            )

        return redirect(
            "attendance:session_list",
            classroom_id=classroom.pk
        )

    form = AttendanceSessionCreateForm(request.POST)

    if not form.is_valid():

        context = {
            "form": form,
            "action_url": request.path,
            "classroom": classroom,
        }

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "attendance/partials/session_create_modal.html",
                context
            )

        messages.error(
            request,
            "Durasi sesi tidak valid."
        )

        return redirect(
            "attendance:session_list",
            classroom_id=classroom.pk
        )

    error_message = None
    success_message = None

    with transaction.atomic():

        locked_classroom = get_object_or_404(
            Classroom.objects.select_for_update(),
            pk=classroom_id,
            teacher=request.user
        )

        expire_due_sessions(locked_classroom)

        active_session_exists = AttendanceSession.objects.filter(
            classroom=locked_classroom,
            status=AttendanceSession.Status.OPEN
        ).exists()

        if active_session_exists:

            error_message = (
                "Masih ada sesi presensi yang aktif di kelas ini."
            )

        else:

            session = AttendanceSession.objects.create(
                classroom=locked_classroom,
                duration_minutes=form.cleaned_data["duration_minutes"]
            )

            student_ids = Enrollment.objects.filter(
                classroom=locked_classroom,
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

            success_message = (
                f"Sesi presensi pertemuan "
                f"{session.meeting_number} berhasil dibuat."
            )

    if error_message:

        if is_ajax_request(request):
            return ajax_error(error_message, status=409)

        messages.warning(request, error_message)

        return redirect(
            "attendance:session_list",
            classroom_id=classroom.pk
        )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect(
        "attendance:session_list",
        classroom_id=classroom.pk
    )


# =========================================================
# MEMBATALKAN SESI PRESENSI
# =========================================================

@login_required
@require_http_methods(["GET", "POST"])
def session_cancel(request, classroom_id, session_id):

    if request.user.role != "TEACHER":
        if is_ajax_request(request):
            return ajax_error(
                "Hanya dosen yang dapat membatalkan sesi.",
                status=403
            )

        return HttpResponseForbidden(
            "Hanya dosen yang dapat membatalkan sesi."
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

    if request.method == "GET":

        if session.status not in [
            AttendanceSession.Status.OPEN,
            AttendanceSession.Status.EXPIRED,
        ]:
            return ajax_error(
                "Sesi ini tidak dapat dibatalkan.",
                status=409
            )

        return render(
            request,
            "attendance/partials/session_cancel_modal.html",
            {
                "form": AttendanceSessionCancelForm(),
                "action_url": request.path,
                "session": session,
            }
        )

    form = AttendanceSessionCancelForm(request.POST)

    if not form.is_valid():

        context = {
            "form": form,
            "action_url": request.path,
            "session": session,
        }

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "attendance/partials/session_cancel_modal.html",
                context
            )

        messages.error(
            request,
            "Alasan pembatalan wajib diisi minimal 5 karakter."
        )

        return redirect(
            "attendance:session_list",
            classroom_id=classroom.pk
        )

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

            error_message = (
                "Sesi ini sudah tidak dapat dibatalkan."
            )

            if is_ajax_request(request):
                return ajax_error(error_message, status=409)

            messages.error(request, error_message)

            return redirect(
                "attendance:session_list",
                classroom_id=classroom.pk
            )

        session.status = AttendanceSession.Status.CANCELLED
        session.closed_at = timezone.now()
        session.cancellation_reason = form.cleaned_data["reason"]

        session.save(update_fields=[
            "status",
            "closed_at",
            "cancellation_reason",
        ])

    success_message = (
        "Sesi presensi berhasil dibatalkan. "
        "Riwayat tetap disimpan."
    )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect(
        "attendance:session_list",
        classroom_id=classroom.pk
    )


# =========================================================
# HELPER FORMULIR PENGISIAN PRESENSI
# =========================================================

def render_student_code_form(
    request,
    classroom,
    form
):
    context = {
        "classroom": classroom,
        "form": form,
        "action_url": request.path,
    }

    if (
        request.GET.get("modal") == "1"
        or is_ajax_request(request)
    ):
        return render(
            request,
            "attendance/partials/student_code_modal.html",
            context
        )

    return render(
        request,
        "attendance/submit_attendance.html",
        context
    )


# =========================================================
# MAHASISWA MENGISI KODE PRESENSI
# =========================================================

@login_required
@require_http_methods(["GET", "POST"])
def student_submit_attendance(request, classroom_id):

    if request.user.role != "STUDENT":
        if is_ajax_request(request):
            return ajax_error(
                "Hanya mahasiswa yang dapat mengisi presensi.",
                status=403
            )

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
        if is_ajax_request(request):
            return ajax_error(
                "Kamu tidak terdaftar sebagai mahasiswa aktif di kelas ini.",
                status=403
            )

        return HttpResponseForbidden(
            "Kamu tidak terdaftar sebagai mahasiswa aktif di kelas ini."
        )

    attempts_key = f"attendance_attempts_user_{request.user.pk}"
    attempts = cache.get(attempts_key, 0)

    if attempts >= 5:

        form = AttendanceCodeForm()

        form.add_error(
            None,
            "Terlalu banyak percobaan kode yang salah. "
            "Silakan coba kembali setelah 10 menit."
        )

        # Ketika mahasiswa mengirim formulir melalui AJAX,
        # respons harus berbentuk JSON seperti respons validasi lain.
        if is_ajax_request(request) and request.method == "POST":

            return ajax_form_error(
                request,
                "attendance/partials/student_code_modal.html",
                {
                    "classroom": classroom,
                    "form": form,
                    "action_url": request.path,
                },
                status=429
            )

        # Untuk GET, template modal tetap dikembalikan sebagai HTML.
        return render_student_code_form(
            request,
            classroom,
            form
        )


    if request.method == "GET":

        return render_student_code_form(
            request,
            classroom,
            AttendanceCodeForm()
        )

    form = AttendanceCodeForm(request.POST)

    if not form.is_valid():

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "attendance/partials/student_code_modal.html",
                {
                    "classroom": classroom,
                    "form": form,
                    "action_url": request.path,
                }
            )

        return render_student_code_form(
            request,
            classroom,
            form
        )

    expire_due_sessions(classroom)

    code = form.cleaned_data["attendance_code"]

    error_message = None
    success_message = None

    with transaction.atomic():

        session = (
            AttendanceSession.objects
            .select_for_update()
            .filter(
                classroom=classroom,
                attendance_code=code,
                status=AttendanceSession.Status.OPEN,
                expires_at__gt=timezone.now()
            )
            .first()
        )

        if not session:

            current_attempts = cache.get(attempts_key, 0)

            cache.set(
                attempts_key,
                current_attempts + 1,
                timeout=600
            )

            error_message = (
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
                    "submitted_at",
                ])

                cache.delete(attempts_key)

                success_message = (
                    "Presensi berhasil dicatat. "
                    "Kamu dinyatakan Hadir."
                )

            else:

                error_message = (
                    "Presensi untuk sesi ini sudah tercatat "
                    "dan tidak dapat diisi kembali."
                )

    if error_message:

        form.add_error(None, error_message)

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "attendance/partials/student_code_modal.html",
                {
                    "classroom": classroom,
                    "form": form,
                    "action_url": request.path,
                },
                status=400
            )

        messages.error(request, error_message)

        return render_student_code_form(
            request,
            classroom,
            form
        )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect(
        "attendance:student_submit",
        classroom_id=classroom.pk
    )


# =========================================================
# MENGUBAH STATUS PRESENSI MAHASISWA
# =========================================================

@login_required
@require_http_methods(["GET", "POST"])
def record_update_status(
    request,
    classroom_id,
    session_id,
    record_id
):

    if request.user.role != "TEACHER":
        if is_ajax_request(request):
            return ajax_error(
                "Hanya dosen yang dapat mengubah status presensi.",
                status=403
            )

        return HttpResponseForbidden(
            "Hanya dosen yang dapat mengubah status presensi."
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

    if session.status not in [
        AttendanceSession.Status.EXPIRED,
        AttendanceSession.Status.CLOSED,
    ]:
        error_message = (
            "Status hanya dapat diubah setelah sesi berakhir "
            "dan selama sesi belum dibatalkan."
        )

        if is_ajax_request(request):
            return ajax_error(error_message, status=409)

        messages.error(request, error_message)

        return redirect(
            "attendance:session_detail",
            classroom_id=classroom.pk,
            session_id=session.pk
        )

    record = get_object_or_404(
        AttendanceRecord.objects.select_related("student"),
        pk=record_id,
        session=session
    )

    initial_status = record.status

    if initial_status == AttendanceRecord.Status.NOT_SUBMITTED:
        initial_status = AttendanceRecord.Status.PRESENT

    if request.method == "GET":

        if request.GET.get("modal") == "1":
            return render(
                request,
                "attendance/partials/status_update_modal.html",
                {
                    "form": AttendanceRecordStatusForm(
                        initial={"status": initial_status}
                    ),
                    "action_url": request.path,
                    "record": record,
                    "session": session,
                }
            )

        return redirect(
            "attendance:session_detail",
            classroom_id=classroom.pk,
            session_id=session.pk
        )

    form = AttendanceRecordStatusForm(request.POST)

    if not form.is_valid():

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "attendance/partials/status_update_modal.html",
                {
                    "form": form,
                    "action_url": request.path,
                    "record": record,
                    "session": session,
                }
            )

        messages.error(
            request,
            "Status atau alasan perubahan tidak valid."
        )

        return redirect(
            "attendance:session_detail",
            classroom_id=classroom.pk,
            session_id=session.pk
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

            error_message = (
                "Sesi tidak lagi mengizinkan perubahan status."
            )

            if is_ajax_request(request):
                return ajax_error(error_message, status=409)

            messages.error(request, error_message)

            return redirect(
                "attendance:session_detail",
                classroom_id=classroom.pk,
                session_id=session.pk
            )

        record = get_object_or_404(
            AttendanceRecord.objects.select_for_update().select_related(
                "student"
            ),
            pk=record_id,
            session=session
        )

        old_status = record.status
        new_status = form.cleaned_data["status"]

        if old_status == new_status:

            success_message = (
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

            success_message = (
                f"Status {record.student.full_name} berhasil diubah "
                f"dari {old_status_label} menjadi {new_status_label}."
            )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect(
        "attendance:session_detail",
        classroom_id=classroom.pk,
        session_id=session.pk
    )
