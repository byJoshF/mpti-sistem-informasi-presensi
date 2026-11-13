from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import ClassroomCreateForm, JoinClassForm
from .models import Classroom, Enrollment


@login_required
def classroom_list(request):
    if request.user.role != "TEACHER":
        return HttpResponseForbidden("Halaman ini hanya untuk dosen.")

    classrooms = Classroom.objects.filter(
        teacher=request.user
    ).order_by("-created_at")

    return render(
        request,
        "classrooms/classroom_list.html",
        {"classrooms": classrooms}
    )


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

            messages.success(
                request,
                f"Kelas '{classroom.name}' berhasil dibuat."
            )

            return redirect("classrooms:classroom_list")

    else:
        form = ClassroomCreateForm()

    return render(
        request,
        "classrooms/classroom_form.html",
        {"form": form}
    )


@login_required
def student_classroom_list(request):
    if request.user.role != "STUDENT":
        return HttpResponseForbidden(
            "Halaman ini hanya untuk mahasiswa."
        )

    enrollments = Enrollment.objects.filter(
        student=request.user,
        is_active=True
    ).select_related(
        "classroom",
        "classroom__teacher"
    ).order_by("-joined_at")

    return render(
        request,
        "classrooms/my_classrooms.html",
        {"enrollments": enrollments}
    )


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

            enrollment, created = Enrollment.objects.get_or_create(
                classroom=classroom,
                student=request.user,
                defaults={"is_active": True}
            )

            if created:
                messages.success(
                    request,
                    f"Berhasil bergabung ke kelas {classroom.name}."
                )

            elif enrollment.is_active:
                messages.info(
                    request,
                    "Kamu sudah terdaftar di kelas tersebut."
                )

            else:
                enrollment.is_active = True
                enrollment.save(update_fields=["is_active"])

                messages.success(
                    request,
                    f"Berhasil bergabung kembali ke kelas {classroom.name}."
                )

            return redirect("classrooms:student_classroom_list")

    else:
        form = JoinClassForm()

    return render(
        request,
        "classrooms/join_class.html",
        {"form": form}
    )


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

    enrollments = Enrollment.objects.filter(
        classroom=classroom,
        is_active=True
    ).select_related("student").order_by("joined_at")

    return render(
        request,
        "classrooms/classroom_detail.html",
        {
            "classroom": classroom,
            "enrollments": enrollments
        }
    )


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

    enrollment.is_active = False
    enrollment.save(update_fields=["is_active"])

    messages.success(
        request,
        f"Mahasiswa {enrollment.student.full_name} berhasil dikeluarkan dari kelas."
    )

    return redirect(
        "classrooms:classroom_detail",
        pk=classroom.pk
    )