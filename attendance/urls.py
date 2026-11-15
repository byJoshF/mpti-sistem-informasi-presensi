
from django.urls import path

from . import views
from . import modal_views
from . import recap_views
from . import student_history_views


app_name = "attendance"


urlpatterns = [

    # DAFTAR SESI
    path(
        "classrooms/<int:classroom_id>/sessions/",
        views.session_list,
        name="session_list"
    ),

    # MEMBUAT SESI
    path(
        "classrooms/<int:classroom_id>/sessions/create/",
        modal_views.session_create,
        name="session_create"
    ),

    # MEMBATALKAN SESI
    path(
        "classrooms/<int:classroom_id>/sessions/<int:session_id>/cancel/",
        modal_views.session_cancel,
        name="session_cancel"
    ),

    # MENGUBAH STATUS PRESENSI
    path(
        "classrooms/<int:classroom_id>/sessions/<int:session_id>/records/<int:record_id>/status/",
        modal_views.record_update_status,
        name="record_update_status"
    ),

    # MAHASISWA MENGISI PRESENSI
    path(
        "classrooms/<int:classroom_id>/submit/",
        modal_views.student_submit_attendance,
        name="student_submit"
    ),

    # REKAP DOSEN
    path(
        "classrooms/<int:classroom_id>/recap/",
        recap_views.semester_recap,
        name="semester_recap"
    ),

    # DETAIL SESI
    path(
        "classrooms/<int:classroom_id>/sessions/<int:session_id>/",
        views.session_detail,
        name="session_detail"
    ),

    # RIWAYAT MAHASISWA
    path(
        "student/history/",
        student_history_views.student_history_list,
        name="student_history_list"
    ),

    path(
        "student/history/classrooms/<int:classroom_id>/",
        student_history_views.student_class_history,
        name="student_class_history"
    ),

]
