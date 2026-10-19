"""
Các trang của Web Portal.

Mỗi view chỉ gọi api_client (HTTP/REST) rồi đưa dữ liệu ra template.
Không có model, không có truy vấn database.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import api_client as api
from .api_client import ApiError, NotFound, ServiceUnavailable
from .forms import RegistrationForm, StudentForm, ThesisForm, translate_error


def fetch(request, func, *args, default=None):
    """Gọi API; nếu service đang tắt thì báo lỗi lên giao diện và trả về default."""
    try:
        return func(*args)
    except ServiceUnavailable as exc:
        messages.error(request, translate_error(str(exc)))
        return default


def count_active_registrations(registrations):
    """Đếm số đăng ký còn hiệu lực (khác REJECTED) theo từng đề tài."""
    counts = {}
    for r in registrations:
        if r["status"] != "REJECTED":
            counts[r["thesis_id"]] = counts.get(r["thesis_id"], 0) + 1
    return counts


# ---------------------------------------------------------------- Dashboard
def dashboard(request):
    students = fetch(request, api.students.list)
    theses = fetch(request, api.theses.list)
    registrations = fetch(request, api.registrations.list)

    counts = count_active_registrations(registrations or [])
    recent_theses = sorted(theses or [], key=lambda t: t["id"], reverse=True)[:5]
    for t in recent_theses:
        t["registered"] = counts.get(t["id"], 0)

    return render(request, "portal/dashboard.html", {
        "menu": "dashboard",
        "total_students": len(students) if students is not None else None,
        "total_theses": len(theses) if theses is not None else None,
        "open_theses": (
            len([t for t in theses if t["status"] == "OPEN"]) if theses is not None else None
        ),
        "total_registrations": len(registrations) if registrations is not None else None,
        "recent_theses": recent_theses,
    })


# ---------------------------------------------------------------- Sinh viên
def student_list(request):
    q = request.GET.get("q", "").strip()
    students = fetch(request, api.students.list, {"search": q} if q else None, default=[])
    return render(request, "portal/student_list.html", {
        "menu": "students", "students": students, "q": q,
    })


def student_form(request, pk=None):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                if pk:
                    api.students.update(pk, form.cleaned_data)
                    messages.success(request, "Cập nhật sinh viên thành công.")
                else:
                    api.students.create(form.cleaned_data)
                    messages.success(request, "Thêm sinh viên thành công.")
                return redirect("student_list")
            except ApiError as exc:
                form.add_api_errors(exc.data)
            except ServiceUnavailable as exc:
                form.add_error(None, translate_error(str(exc)))
    else:
        initial = None
        if pk:
            try:
                initial = api.students.get(pk)
            except (NotFound, ServiceUnavailable):
                messages.error(request, "Không tải được thông tin sinh viên.")
                return redirect("student_list")
        form = StudentForm(initial=initial)

    return render(request, "portal/student_form.html", {
        "menu": "students", "form": form, "is_edit": bool(pk),
    })


@require_POST
def student_delete(request, pk):
    try:
        api.students.delete(pk)
        messages.success(request, "Đã xóa sinh viên.")
    except NotFound:
        messages.error(request, "Sinh viên không tồn tại.")
    except ServiceUnavailable as exc:
        messages.error(request, translate_error(str(exc)))
    return redirect("student_list")


# ---------------------------------------------------------------- Đề tài
def thesis_list(request):
    q = request.GET.get("q", "").strip()
    theses = fetch(request, api.theses.list, {"search": q} if q else None, default=[])
    registrations = fetch(request, api.registrations.list, default=[])
    counts = count_active_registrations(registrations)
    for t in theses:
        t["registered"] = counts.get(t["id"], 0)
    return render(request, "portal/thesis_list.html", {
        "menu": "theses", "theses": theses, "q": q,
    })


def thesis_form(request, pk=None):
    if request.method == "POST":
        form = ThesisForm(request.POST)
        if form.is_valid():
            try:
                if pk:
                    api.theses.update(pk, form.cleaned_data)
                    messages.success(request, "Cập nhật đề tài thành công.")
                else:
                    api.theses.create(form.cleaned_data)
                    messages.success(request, "Thêm đề tài thành công.")
                return redirect("thesis_list")
            except ApiError as exc:
                form.add_api_errors(exc.data)
            except ServiceUnavailable as exc:
                form.add_error(None, translate_error(str(exc)))
    else:
        initial = None
        if pk:
            try:
                initial = api.theses.get(pk)
            except (NotFound, ServiceUnavailable):
                messages.error(request, "Không tải được thông tin đề tài.")
                return redirect("thesis_list")
        form = ThesisForm(initial=initial)

    return render(request, "portal/thesis_form.html", {
        "menu": "theses", "form": form, "is_edit": bool(pk),
    })


@require_POST
def thesis_delete(request, pk):
    try:
        api.theses.delete(pk)
        messages.success(request, "Đã xóa đề tài.")
    except NotFound:
        messages.error(request, "Đề tài không tồn tại.")
    except ServiceUnavailable as exc:
        messages.error(request, translate_error(str(exc)))
    return redirect("thesis_list")


# ---------------------------------------------------------------- Đăng ký
def registration_list(request):
    # Bộ lọc gửi thẳng sang Registration Service: ?student_id=&thesis_id=&status=
    filters = {
        key: request.GET[key]
        for key in ("student_id", "thesis_id", "status")
        if request.GET.get(key)
    }
    registrations = fetch(request, api.registrations.list, filters, default=[])
    students = fetch(request, api.students.list, default=[])
    theses = fetch(request, api.theses.list, default=[])

    if not request.user.is_staff:
        own_student = next(
            (
                student for student in students
                if student["student_code"].casefold() == request.user.username.casefold()
            ),
            None,
        )
        if own_student:
            registrations = [
                registration for registration in registrations
                if registration["student_id"] == own_student["id"]
            ]
            students = [own_student]
        else:
            registrations = []
            students = []

    # Ghép tên sinh viên / đề tài theo id (dữ liệu nằm ở 2 service khác)
    student_map = {s["id"]: s for s in students}
    thesis_map = {t["id"]: t for t in theses}
    for r in registrations:
        r["student"] = student_map.get(r["student_id"])
        r["thesis"] = thesis_map.get(r["thesis_id"])
        r["registered_at"] = parse_datetime(r["registered_at"])

    return render(request, "portal/registration_list.html", {
        "menu": "registrations",
        "registrations": registrations,
        "students": students,
        "theses": theses,
        "filters": filters,
        "statuses": [("PENDING", "Chờ duyệt"), ("APPROVED", "Đã duyệt"), ("REJECTED", "Từ chối")],
    })


def registration_create(request):
    students = fetch(request, api.students.list, default=[])
    theses = fetch(request, api.theses.list, default=[])

    own_student = None
    if not request.user.is_staff:
        own_student = next(
            (
                student for student in students
                if student["student_code"].casefold() == request.user.username.casefold()
            ),
            None,
        )
        if own_student is None:
            messages.error(
                request,
                "Tên đăng nhập phải khớp mã sinh viên đã được tạo trong hệ thống.",
            )
            return redirect("registration_list")
        students = [own_student]

    form = RegistrationForm(request.POST or None, students=students, theses=theses)
    if request.method == "POST" and form.is_valid():
        try:
            # Registration Service sẽ tự gọi Student Service + Thesis Service để kiểm tra
            data = form.cleaned_data
            if own_student:
                data["student_id"] = own_student["id"]
            api.registrations.create(data)
            messages.success(request, "Đăng ký đề tài thành công.")
            return redirect("registration_list")
        except ApiError as exc:
            form.add_api_errors(exc.data)
        except ServiceUnavailable as exc:
            form.add_error(None, translate_error(str(exc)))

    return render(request, "portal/registration_form.html", {
        "menu": "registrations", "form": form,
    })


@require_POST
def registration_status(request, pk):
    new_status = request.POST.get("status")
    try:
        api.registrations.update(pk, {"status": new_status})
        messages.success(request, "Đã cập nhật trạng thái đăng ký.")
    except ApiError as exc:
        messages.error(request, translate_error(exc.data.get("error", str(exc.data))))
    except NotFound:
        messages.error(request, "Đăng ký không tồn tại.")
    except ServiceUnavailable as exc:
        messages.error(request, translate_error(str(exc)))
    return redirect("registration_list")


@require_POST
def registration_delete(request, pk):
    try:
        api.registrations.delete(pk)
        messages.success(request, "Đã xóa đăng ký.")
    except NotFound:
        messages.error(request, "Đăng ký không tồn tại.")
    except ServiceUnavailable as exc:
        messages.error(request, translate_error(str(exc)))
    return redirect("registration_list")


# ---------------------------------------------------------------- API Docs
def api_docs(request):
    services = [
        ("Student Service", "Quản lý sinh viên", settings.STUDENT_SERVICE_URL, "student_db"),
        ("Thesis Service", "Quản lý đề tài", settings.THESIS_SERVICE_URL, "thesis_db"),
        ("Registration Service", "Quản lý đăng ký", settings.REGISTRATION_SERVICE_URL, "registration_db"),
    ]
    rows = [
        {"name": name, "desc": desc, "url": url, "db": db, "online": api.is_online(url)}
        for name, desc, url, db in services
    ]
    return render(request, "portal/api_docs.html", {"menu": "api_docs", "services": rows})

# --------------------------------------------------------------------Đăng nhập
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.POST.get("next") or request.GET.get("next", "")
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("dashboard")

    return render(
        request,
        "portal/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


#------------------------------------------------------------------- Đăng ký tài khoản
def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["username"].casefold() == "admin123":
            form.add_error("username", "Tên đăng nhập này được dành riêng cho quản trị viên.")
            return render(request, "portal/register.html", {"form": form})

        user = form.save()
        user.is_active = False
        user.save(update_fields=["is_active"])
        student_group, _ = Group.objects.get_or_create(name="student")
        user.groups.add(student_group)
        messages.success(
            request,
            "Đăng ký thành công. Quản trị viên cần kích hoạt tài khoản trước khi đăng nhập.",
        )
        return redirect("login")

    return render(
        request,
        "portal/register.html",
        {"form": form}
    )


#----------------------------------------------------------------------- Đăng xuất
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "Bạn đã đăng xuất.")

    return redirect("login")
