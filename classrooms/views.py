from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Lower
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from attendance.models import AttendanceSession, AttendanceRecord

from .forms import (
    ClassroomCreateForm,
    JoinClassForm,
)

from .models import Classroom, Enrollment, EnrollmentPeriod


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


def ajax_form_error(request, template_name, context):
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
        status=400
    )


# =========================================================
# HELPER KEANGGOTAAN DAN PRESENSI
# =========================================================

def create_missing_attendance_records(classroom, student):
    """Buat record Belum Mengisi untuk seluruh sesi resmi; jangan timpa record lama."""
    sessions = (
        AttendanceSession.objects
        .filter(classroom=classroom)
        .exclude(status=AttendanceSession.Status.CANCELLED)
        .only("pk")
    )
    AttendanceRecord.objects.bulk_create(
        [AttendanceRecord(session=session, student=student) for session in sessions],
        ignore_conflicts=True
    )


def ensure_active_period(enrollment):
    period = (
        enrollment.periods
        .filter(is_active=True)
        .order_by("-joined_at")
        .first()
    )

    if period is None:
        period = EnrollmentPeriod.objects.create(
            enrollment=enrollment,
            joined_at=enrollment.joined_at,
            is_active=True
        )

    return period


def close_active_period(enrollment):
    EnrollmentPeriod.objects.filter(
        enrollment=enrollment,
        is_active=True
    ).update(
        is_active=False,
        left_at=timezone.now()
    )


# =========================================================
# DAFTAR KELAS DOSEN
# =========================================================

@login_required
def classroom_list(request):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk dosen."
        )

    search_query = request.GET.get("q", "").strip()

    attendance_history = AttendanceSession.objects.filter(
        classroom_id=OuterRef("pk")
    )

    classrooms = Classroom.objects.filter(
        teacher=request.user
    ).annotate(
        has_attendance_history=Exists(attendance_history)
    )

    if search_query:
        classrooms = classrooms.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(join_code__icontains=search_query)
        )

    classrooms = classrooms.order_by("-created_at")

    return render(
        request,
        "classrooms/classroom_list.html",
        {
            "classrooms": classrooms,
            "search_query": search_query,
        }
    )


# =========================================================
# MEMBUAT KELAS
# =========================================================

@login_required
def classroom_create(request):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat membuat kelas."
        )

    if request.method == "POST":
        form = ClassroomCreateForm(request.POST)

        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.teacher = request.user
            classroom.save()

            success_message = (
                f"Kelas '{classroom.name}' berhasil dibuat."
            )

            messages.success(request, success_message)

            if is_ajax_request(request):
                return ajax_success(success_message)

            return redirect("classrooms:classroom_list")

        context = {
            "form": form,
            "action_url": request.path,
            "is_edit": False,
        }

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "classrooms/partials/classroom_form_modal.html",
                context
            )

    else:
        form = ClassroomCreateForm()

    context = {
        "form": form,
        "action_url": request.path,
        "is_edit": False,
    }

    if request.GET.get("modal") == "1":
        return render(
            request,
            "classrooms/partials/classroom_form_modal.html",
            context
        )

    return render(
        request,
        "classrooms/classroom_form.html",
        context
    )


# =========================================================
# DAFTAR KELAS MAHASISWA
# =========================================================

@login_required
def student_classroom_list(request):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk mahasiswa."
        )

    active_sessions = AttendanceSession.objects.filter(
        classroom_id=OuterRef("classroom_id"),
        status=AttendanceSession.Status.OPEN,
        expires_at__gt=timezone.now()
    )

    enrollments = (
        Enrollment.objects
        .filter(
            student=request.user,
            is_active=True
        )
        .select_related(
            "classroom",
            "classroom__teacher"
        )
        .prefetch_related("periods")
        .annotate(
            has_active_session=Exists(active_sessions)
        )
        .order_by(
            "-has_active_session",
            "-joined_at"
        )
    )

    for enrollment in enrollments:
        enrollment.current_period = next(
            (
                period
                for period in enrollment.periods.all()
                if period.is_active
            ),
            None
        )

    return render(
        request,
        "classrooms/my_classrooms.html",
        {"enrollments": enrollments}
    )


# =========================================================
# MAHASISWA BERGABUNG KE KELAS
# =========================================================

@login_required
def classroom_join(request):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden(
            "Hanya mahasiswa yang dapat bergabung ke kelas."
        )

    if request.method == "POST":
        form = JoinClassForm(request.POST)

        if form.is_valid():
            classroom = get_object_or_404(
                Classroom,
                join_code=form.cleaned_data["join_code"]
            )

            now = timezone.now()
            with transaction.atomic():
                enrollment, created = Enrollment.objects.get_or_create(
                    classroom=classroom,
                    student=request.user,
                    defaults={"is_active": True}
                )
                if created:
                    EnrollmentPeriod.objects.create(
                        enrollment=enrollment, joined_at=now, is_active=True
                    )
                    create_missing_attendance_records(classroom, request.user)
                    success_message = (
                        f"Berhasil bergabung ke kelas {classroom.name}. "
                        "Riwayat sesi sebelumnya juga telah disiapkan."
                    )
                    messages.success(request, success_message)
                elif enrollment.is_active:
                    ensure_active_period(enrollment)
                    success_message = "Kamu sudah terdaftar di kelas tersebut."
                    messages.info(request, success_message)
                else:
                    close_active_period(enrollment)
                    enrollment.is_active = True
                    enrollment.save(update_fields=["is_active"])
                    EnrollmentPeriod.objects.create(
                        enrollment=enrollment, joined_at=now, is_active=True
                    )
                    create_missing_attendance_records(classroom, request.user)
                    success_message = (
                        f"Berhasil bergabung kembali ke kelas {classroom.name}. "
                        "Riwayat kehadiran sebelumnya dan sesi yang terlewat tetap dipertahankan."
                    )
                    messages.success(request, success_message)

            if is_ajax_request(request):
                return ajax_success(success_message)

            return redirect(
                "classrooms:student_classroom_list"
            )

        context = {
            "form": form,
            "action_url": request.path,
        }

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "classrooms/partials/join_class_modal.html",
                context
            )

    else:
        form = JoinClassForm()

    context = {
        "form": form,
        "action_url": request.path,
    }

    if request.GET.get("modal") == "1":
        return render(
            request,
            "classrooms/partials/join_class_modal.html",
            context
        )

    return render(
        request,
        "classrooms/join_class.html",
        context
    )


# =========================================================
# DETAIL KELAS DOSEN
# =========================================================

@login_required
def classroom_detail(request, pk):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk dosen."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user
    )

    # Mahasiswa aktif diurutkan berdasarkan nama lengkap A-Z.
    # Jika nama sama, username/NIM menjadi urutan berikutnya.
    enrollments = (
        Enrollment.objects
        .filter(
            classroom=classroom,
            is_active=True
        )
        .select_related("student")
        .prefetch_related("periods")
        .order_by(
            Lower("student__full_name"),
            "student__username"
        )
    )

    # Mantan anggota kelas juga diurutkan A-Z agar konsisten.
    inactive_enrollments = (
        Enrollment.objects
        .filter(
            classroom=classroom,
            is_active=False
        )
        .select_related("student")
        .prefetch_related("periods")
        .order_by(
            Lower("student__full_name"),
            "student__username"
        )
    )

    return render(
        request,
        "classrooms/classroom_detail.html",
        {
            "classroom": classroom,
            "enrollments": enrollments,
            "inactive_enrollments": inactive_enrollments,
            "has_attendance_history": (
                classroom.attendance_sessions.exists()
            ),
        }
    )


# =========================================================
# DOSEN MENGELUARKAN MAHASISWA
# =========================================================

@login_required
@require_POST
def enrollment_remove(request, pk, enrollment_id):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat mengelola peserta kelas."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user
    )

    enrollment = get_object_or_404(
        Enrollment,
        pk=enrollment_id,
        classroom=classroom,
        is_active=True
    )

    with transaction.atomic():
        close_active_period(enrollment)

        enrollment.is_active = False
        enrollment.save(update_fields=["is_active"])

    success_message = (
        f"Mahasiswa {enrollment.student.full_name} "
        "berhasil dikeluarkan dari kelas. Riwayatnya tetap disimpan."
    )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect(
        "classrooms:classroom_detail",
        pk=classroom.pk
    )


# =========================================================
# MAHASISWA KELUAR DARI KELAS
# =========================================================

@login_required
@require_POST
def student_leave_class(request, pk):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden(
            "Hanya mahasiswa yang dapat keluar dari kelas."
        )

    enrollment = get_object_or_404(
        Enrollment.objects.select_related("classroom"),
        classroom_id=pk,
        student=request.user,
        is_active=True
    )

    with transaction.atomic():
        close_active_period(enrollment)

        enrollment.is_active = False
        enrollment.save(update_fields=["is_active"])

    success_message = (
        f"Kamu berhasil keluar dari kelas "
        f"{enrollment.classroom.name}. "
        "Riwayat presensimu tetap disimpan."
    )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect(
        "classrooms:student_classroom_list"
    )


# =========================================================
# EDIT KELAS
# =========================================================

@login_required
def classroom_edit(request, pk):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat mengedit kelas."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user
    )

    if request.method == "POST":
        form = ClassroomCreateForm(
            request.POST,
            instance=classroom
        )

        if form.is_valid():
            form.save()

            success_message = (
                "Informasi kelas berhasil diperbarui."
            )

            messages.success(request, success_message)

            if is_ajax_request(request):
                return ajax_success(success_message)

            return redirect(
                "classrooms:classroom_detail",
                pk=classroom.pk
            )

        context = {
            "form": form,
            "action_url": request.path,
            "is_edit": True,
            "classroom": classroom,
        }

        if is_ajax_request(request):
            return ajax_form_error(
                request,
                "classrooms/partials/classroom_form_modal.html",
                context
            )

    else:
        form = ClassroomCreateForm(instance=classroom)

    context = {
        "form": form,
        "action_url": request.path,
        "is_edit": True,
        "classroom": classroom,
    }

    if request.GET.get("modal") == "1":
        return render(
            request,
            "classrooms/partials/classroom_form_modal.html",
            context
        )

    return render(
        request,
        "classrooms/classroom_form.html",
        context
    )


# =========================================================
# HAPUS KELAS
# =========================================================

@login_required
@require_POST
def classroom_delete(request, pk):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden(
            "Hanya dosen yang dapat menghapus kelas."
        )

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user
    )

    if classroom.attendance_sessions.exists():
        error_message = (
            "Kelas tidak dapat dihapus karena sudah memiliki "
            "riwayat sesi absensi. Data presensi harus dipertahankan."
        )

        messages.error(request, error_message)

        if is_ajax_request(request):
            return JsonResponse(
                {
                    "success": False,
                    "message": error_message,
                },
                status=400
            )

        return redirect(
            "classrooms:classroom_detail",
            pk=classroom.pk
        )

    classroom_name = classroom.name
    classroom.delete()

    success_message = (
        f"Kelas '{classroom_name}' berhasil dihapus."
    )

    messages.success(request, success_message)

    if is_ajax_request(request):
        return ajax_success(success_message)

    return redirect("classrooms:classroom_list")