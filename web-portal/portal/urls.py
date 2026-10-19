from django.urls import path

from . import views
from django.contrib.auth.decorators import login_required, user_passes_test


admin_required = user_passes_test(
    lambda user: user.is_authenticated and user.is_staff
)

urlpatterns = [
    path("", login_required(views.dashboard), name="dashboard"),

    path("sinh-vien/", login_required(views.student_list), name="student_list"),
    path("sinh-vien/them/", admin_required(views.student_form), name="student_create"),
    path("sinh-vien/<int:pk>/sua/", admin_required(views.student_form), name="student_edit"),
    path("sinh-vien/<int:pk>/xoa/", admin_required(views.student_delete), name="student_delete"),

    path("de-tai/", login_required(views.thesis_list), name="thesis_list"),
    path("de-tai/them/", admin_required(views.thesis_form), name="thesis_create"),
    path("de-tai/<int:pk>/sua/", admin_required(views.thesis_form), name="thesis_edit"),
    path("de-tai/<int:pk>/xoa/", admin_required(views.thesis_delete), name="thesis_delete"),

    path("dang-ky/", login_required(views.registration_list), name="registration_list"),
    path("dang-ky/them/", login_required(views.registration_create), name="registration_create"),
    path("dang-ky/<int:pk>/trang-thai/", admin_required(views.registration_status), name="registration_status"),
    path("dang-ky/<int:pk>/xoa/", admin_required(views.registration_delete), name="registration_delete"),

    path("api-docs/", login_required(views.api_docs), name="api_docs"),

    path("dang-nhap/", views.login_view, name="login"),
    path("dang-ky-tai-khoan/", views.register_view, name="register"),
    path("dang-xuat/", views.logout_view, name="logout"),
]
