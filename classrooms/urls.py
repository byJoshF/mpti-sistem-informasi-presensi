from django.urls import path
from . import views

app_name = "classrooms"

urlpatterns = [
    path("", views.classroom_list, name="classroom_list"),
    path("create/", views.classroom_create, name="classroom_create"),

    path("my-classes/", views.student_classroom_list, name="student_classroom_list"),
    path("join/", views.classroom_join, name="classroom_join"),

    path(
        "<int:pk>/members/<int:enrollment_id>/remove/",
        views.enrollment_remove,
        name="enrollment_remove"
    ),

    path(
        "<int:pk>/leave/",
        views.student_leave_class,
        name="student_leave_class"
    ),

    path("<int:pk>/edit/", views.classroom_edit, name="classroom_edit"),
    path("<int:pk>/delete/", views.classroom_delete, name="classroom_delete"),
    path("<int:pk>/", views.classroom_detail, name="classroom_detail"),
]