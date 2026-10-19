"""
Test Web Portal. 3 service được giả lập bằng cách mock requests.request,
nên không cần chạy service nào khi chạy test.
"""
from copy import deepcopy
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase

STUDENTS = [{"id": 1, "student_code": "SV001", "full_name": "Nguyễn Văn An",
             "email": "an@x.vn", "class_name": "CNTT1", "major": "CNTT"}]
THESES = [{"id": 1, "thesis_code": "DT001", "title": "Hệ thống quản lý thư viện",
           "description": "", "supervisor": "TS. A", "max_students": 2, "status": "OPEN"}]
REGISTRATIONS = [{"id": 1, "student_id": 1, "thesis_id": 1,
                  "registered_at": "2026-10-04T10:00:00+07:00", "status": "PENDING"}]


def make_response(status_code, data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = deepcopy(data)
    response.content = b"x" if data is not None else b""
    return response


def fake_request(method, url, timeout=None, **kwargs):
    if method == "GET":
        if "/api/students/" in url:
            return make_response(200, STUDENTS)
        if "/api/theses/" in url:
            return make_response(200, THESES)
        if "/api/registrations/" in url:
            return make_response(200, REGISTRATIONS)
    if method == "POST" and "/api/registrations/" in url:
        return make_response(400, {"error": "Thesis is closed"})
    if method == "POST" and "/api/students/" in url:
        return make_response(201, {"id": 2, **kwargs["json"]})
    raise AssertionError(f"Unexpected {method} {url}")


@patch("portal.api_client.requests.request", side_effect=fake_request)
class PortalPageTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="test-admin",
            password="strong-test-password",
            is_staff=True,
        )
        self.client.force_login(user)

    def test_dashboard_requires_login(self, mock_request):
        self.client.cookies.clear()
        response = self.client.get("/")
        self.assertRedirects(
            response,
            "/dang-nhap/?next=/",
            fetch_redirect_response=False,
        )

    def test_dashboard(self, mock_request):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_students"], 1)
        self.assertEqual(response.context["open_theses"], 1)
        self.assertContains(response, "Đề tài gần đây")

    def test_student_list(self, mock_request):
        response = self.client.get("/sinh-vien/")
        self.assertContains(response, "Nguyễn Văn An")

    def test_registration_list_shows_names_from_other_services(self, mock_request):
        response = self.client.get("/dang-ky/")
        self.assertContains(response, "SV001 - Nguyễn Văn An")
        self.assertContains(response, "DT001 - Hệ thống quản lý thư viện")
        self.assertContains(response, "Chờ duyệt")

    def test_student_sees_only_own_registrations(self, mock_request):
        student = get_user_model().objects.create_user(
            username="SV001",
            password="strong-test-password",
        )
        self.client.force_login(student)

        response = self.client.get("/dang-ky/")

        self.assertContains(response, "SV001 - Nguyễn Văn An")
        self.assertNotContains(response, "SV002 - Trần Văn Bình")

    def test_create_student_redirects(self, mock_request):
        data = {"student_code": "SV002", "full_name": "Trần Văn Bình", "email": "binh@x.vn"}
        response = self.client.post("/sinh-vien/them/", data)
        self.assertRedirects(response, "/sinh-vien/", fetch_redirect_response=False)

    def test_registration_error_from_api_is_shown(self, mock_request):
        response = self.client.post("/dang-ky/them/", {"student_id": 1, "thesis_id": 1})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Đề tài đã đóng, không thể đăng ký.")


@patch("portal.api_client.requests.request", side_effect=requests.ConnectionError())
class ServiceDownTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="test-admin",
            password="strong-test-password",
            is_staff=True,
        )
        self.client.force_login(user)

    def test_dashboard_still_renders_when_services_down(self, mock_request):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Service không hoạt động")


class PortalAuthenticationTests(TestCase):
    def test_login_authenticates_portal_user(self):
        get_user_model().objects.create_user(
            username="student1",
            password="strong-test-password",
        )
        response = self.client.post(
            "/dang-nhap/",
            {"username": "student1", "password": "strong-test-password"},
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_creates_inactive_student_account(self):
        response = self.client.post(
            "/dang-ky-tai-khoan/",
            {
                "username": "new-student",
                "password1": "strong-test-password",
                "password2": "strong-test-password",
            },
        )

        self.assertRedirects(response, "/dang-nhap/", fetch_redirect_response=False)
        user = get_user_model().objects.get(username="new-student")
        self.assertFalse(user.is_active)
        self.assertTrue(user.groups.filter(name="student").exists())

    def test_non_admin_cannot_delete_thesis(self):
        get_user_model().objects.create_user(
            username="student2",
            password="strong-test-password",
        )
        self.client.login(username="student2", password="strong-test-password")

        response = self.client.post("/de-tai/1/xoa/")

        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, "/de-tai/")
