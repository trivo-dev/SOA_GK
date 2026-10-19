# Hệ thống quản lý đồ án tốt nghiệp — Demo SOA (Django + DRF + PostgreSQL)

## 1. Giới thiệu

Project demo giữa kỳ môn **Công nghệ phần mềm**. Khoa cần quản lý việc sinh viên đăng ký đề tài đồ án tốt nghiệp.

Hệ thống được xây dựng theo **kiến trúc hướng dịch vụ (SOA)**: gồm **3 Web Service độc lập**, mỗi service có database riêng và giao tiếp với nhau qua **HTTP/REST (JSON)**.

| Service              | Trách nhiệm         | Port | Database          | Bảng       |
| -------------------- | ------------------- | ---- | ----------------- | ---------- |
| Student Service      | Quản lý sinh viên   | 8001 | `student_db`      | `sinhvien` |
| Thesis Service       | Quản lý đề tài      | 8002 | `thesis_db`       | `detai`    |
| Registration Service | Quản lý đăng ký     | 8003 | `registration_db` | `dangky`   |
| Web Portal (giao diện) | Giao diện và tài khoản người dùng | 8000 | `portal_db` | Django auth/session |

**Giao diện web:** http://127.0.0.1:8000/. Portal lưu tài khoản và session trong `portal_db`; dữ liệu sinh viên, đề tài và đăng ký vẫn chỉ thuộc database của từng service.

## 2. Kiến trúc SOA

```
              Trình duyệt ──► Web Portal :8000 (Django template + Bootstrap 5)
                                     │ gọi REST API của cả 3 service
                 ┌───────────────────┼─────────────────────────┐
                 │   (hoặc Swagger UI / Postman / curl)        │
                 ▼                      ▼                         ▼
                 ▼                      ▼                         ▼
      ┌──────────────────┐   ┌──────────────────┐   ┌─────────────────────────┐
      │ Student Service  │   │  Thesis Service  │   │  Registration Service   │
      │   :8001          │   │   :8002          │   │   :8003                 │
      │ /api/students/   │   │ /api/theses/     │   │ /api/registrations/     │
      └────────┬─────────┘   └────────┬─────────┘   └──┬───────────┬──────────┘
               │                      │                │           │
               │   ◄── HTTP GET /api/students/{id}/ ───┘           │
               │                      │   ◄── HTTP GET /api/theses/{id}/
               ▼                      ▼                            ▼
          student_db             thesis_db                 registration_db
```

- Mỗi service là **một Django project riêng**, chạy **một process riêng**, trên **một port riêng**.
- Mỗi service **chỉ kết nối database của chính nó**.
- Registration Service **không có ForeignKey** tới Student/Thesis: bảng `dangky` chỉ lưu `student_id`, `thesis_id` (số nguyên). Muốn biết sinh viên/đề tài có tồn tại hay không thì **gọi REST API** của service tương ứng.

## 3. Công nghệ sử dụng

- Python 3.12+ (đã chạy thử với Python 3.14)
- Django, Django REST Framework
- PostgreSQL (driver `psycopg` 3)
- `requests` — Registration Service dùng để gọi HTTP sang các service khác
- `drf-spectacular` — sinh tài liệu OpenAPI + Swagger UI
- `python-dotenv` — đọc cấu hình từ file `.env`

## 4. Cấu trúc project

```
Demo_GK/
├── README.md
├── student-service/                  # Port 8001 - student_db
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/                       # settings.py, urls.py (Swagger tại /api/docs/)
│   └── students/
│       ├── models.py                 # Model Student (bảng sinhvien)
│       ├── serializers.py            # Validation
│       ├── views.py                  # ListCreateAPIView, RetrieveUpdateDestroyAPIView
│       ├── urls.py
│       ├── admin.py
│       ├── tests.py
│       └── management/commands/seed_data.py
│
├── thesis-service/                   # Port 8002 - thesis_db
│   └── theses/  (cấu trúc giống students/)
│
├── registration-service/             # Port 8003 - registration_db
│   ├── .env.example                  # có thêm STUDENT_SERVICE_URL, THESIS_SERVICE_URL
│   └── registrations/
│       ├── models.py                 # Registration: student_id, thesis_id KHÔNG phải ForeignKey
│       ├── serializers.py
│       ├── views.py                  # Luồng nghiệp vụ đăng ký (bước 1 → 5)
│       ├── urls.py
│       ├── services/
│       │   └── external_api.py       # ★ Toàn bộ code gọi HTTP sang Student/Thesis Service
│       ├── tests.py                  # Mock HTTP bằng unittest.mock
│       └── management/commands/seed_data.py
│
├── web-portal/                       # Port 8000 - giao diện web, portal_db lưu tài khoản
│   ├── .env.example                  # URL của 3 service
│   └── portal/
│       ├── api_client.py             # Gọi REST API của 3 service (requests)
│       ├── forms.py                  # Form Django (thêm/sửa sinh viên, đề tài, đăng ký)
│       ├── views.py                  # Dashboard, Sinh viên, Đề tài, Đăng ký, API Docs
│       ├── urls.py
│       ├── templates/portal/         # Bootstrap 5: base.html, *_list.html, *_form.html
│       └── tests.py
│
└── run_all.bat                       # Mở 4 cửa sổ chạy 4 service cùng lúc
```

## 5. Cấu hình PostgreSQL

Mỗi service đọc cấu hình từ file `.env` của riêng nó (không hard-code trong code). Tạo `.env` từ `.env.example`:

```powershell
copy student-service\.env.example       student-service\.env
copy thesis-service\.env.example        thesis-service\.env
copy registration-service\.env.example  registration-service\.env
copy web-portal\.env.example            web-portal\.env
```

Sửa `DB_PASSWORD` cho đúng mật khẩu PostgreSQL trên máy. Ví dụ `student-service/.env`:

```
DB_NAME=student_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

`registration-service/.env` có thêm địa chỉ các service khác:

```
STUDENT_SERVICE_URL=http://127.0.0.1:8001
THESIS_SERVICE_URL=http://127.0.0.1:8002
```

## 6. Tạo database

Một PostgreSQL server, 4 database riêng. Dùng `psql` (hoặc pgAdmin):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost
```

```sql
CREATE DATABASE student_db;
CREATE DATABASE thesis_db;
CREATE DATABASE registration_db;
CREATE DATABASE portal_db;
```

## 7. Cài requirements

Dùng một virtualenv chung ở thư mục gốc (mỗi service vẫn có `requirements.txt` riêng):

```powershell
cd D:\SOA\Demo_GK
python -m venv .venv
.venv\Scripts\activate
pip install -r student-service\requirements.txt -r thesis-service\requirements.txt -r registration-service\requirements.txt -r web-portal\requirements.txt
```

> Nếu PowerShell chặn `activate`: chạy `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` một lần.

Tạo bảng (migrate) cho từng service:

```powershell
cd student-service;      python manage.py migrate; cd ..
cd thesis-service;       python manage.py migrate; cd ..
cd registration-service; python manage.py migrate; cd ..
cd web-portal;           python manage.py migrate; cd ..
```

## 8. Chạy từng service

**Cách nhanh:** bấm đúp file `run_all.bat`. File này mở 4 cửa sổ, mỗi cửa sổ chạy một service. Sau đó mở http://127.0.0.1:8000/.

**Cách thủ công:** mở 4 cửa sổ terminal (đã `activate` venv ở mỗi cửa sổ):

```powershell
# Terminal 1
cd student-service
python manage.py runserver 8001

# Terminal 2
cd thesis-service
python manage.py runserver 8002

# Terminal 3
cd registration-service
python manage.py runserver 8003

# Terminal 4 - giao diện web
cd web-portal
python manage.py runserver 8000
```

Tạo dữ liệu mẫu (mở thêm một terminal, **sau khi các service đang chạy**):

```powershell
cd student-service;      python manage.py seed_data; cd ..
cd thesis-service;       python manage.py seed_data; cd ..
cd registration-service; python manage.py seed_data; cd ..
```

> `seed_data` của Registration Service cũng **lấy id sinh viên/đề tài qua REST API**, nên phải chạy 2 service kia trước. Chạy `seed_data` nhiều lần không bị trùng dữ liệu.

Dữ liệu mẫu:

| Sinh viên                     | Đề tài                                                       |
| ----------------------------- | ------------------------------------------------------------ |
| id=1 SV001 - Nguyễn Văn An    | id=1 DT001 - Hệ thống quản lý thư viện (OPEN, tối đa 3)      |
| id=2 SV002 - Trần Văn Bình    | id=2 DT002 - Hệ thống đặt sân thể thao (OPEN, tối đa 1)      |
| id=3 SV003 - Lê Văn Cường     | id=3 DT003 - Hệ thống quản lý đồ án tốt nghiệp (**CLOSED**)  |

| Đăng ký | Sinh viên | Đề tài | Trạng thái |
| ------- | --------- | ------ | ---------- |
| 1       | SV001     | DT001  | APPROVED   |
| 2       | SV002     | DT001  | PENDING    |
| 3       | SV003     | DT002  | APPROVED   |

Chạy test (không cần chạy service — HTTP được mock; Django tự tạo database test tạm):

```powershell
cd student-service;      python manage.py test; cd ..
cd thesis-service;       python manage.py test; cd ..
cd registration-service; python manage.py test; cd ..
cd web-portal;           python manage.py test; cd ..
```

### Giao diện web (Web Portal — http://127.0.0.1:8000/)

| Menu       | Chức năng                                                                 |
| ---------- | ------------------------------------------------------------------------- |
| Dashboard  | Tổng số sinh viên, đề tài, đề tài đang mở, đăng ký; bảng "Đề tài gần đây" |
| Sinh viên  | Danh sách, tìm kiếm, thêm, sửa, xóa                                       |
| Đề tài     | Danh sách (kèm số đã đăng ký / tối đa), tìm kiếm, thêm, sửa, xóa          |
| Đăng ký    | Danh sách, lọc theo sinh viên/đề tài/trạng thái, đăng ký mới, duyệt, từ chối, xóa |
| API Docs   | Trạng thái 3 service (hoạt động / không) và link Swagger của từng service |

Web Portal dùng `portal_db` riêng để lưu tài khoản và session Django; dữ liệu nghiệp vụ vẫn được lấy qua REST API của 3 service (`portal/api_client.py`). Ví dụ bảng Đăng ký: lấy danh sách đăng ký từ Registration Service, sau đó lấy tên sinh viên từ Student Service và tên đề tài từ Thesis Service rồi ghép lại để hiển thị. Nếu một service bị tắt, trang vẫn mở được và hiện thông báo "... Service không hoạt động".

## 9. Danh sách API

### Student Service — `http://127.0.0.1:8001`

| Method | URL                           | Mô tả                    |
| ------ | ----------------------------- | ------------------------ |
| GET    | `/api/students/`              | Danh sách sinh viên      |
| GET    | `/api/students/?search=Nguyen`| Tìm kiếm (có/không dấu)  |
| POST   | `/api/students/`              | Tạo sinh viên            |
| GET    | `/api/students/{id}/`         | Chi tiết                 |
| PUT    | `/api/students/{id}/`         | Cập nhật toàn bộ         |
| PATCH  | `/api/students/{id}/`         | Cập nhật một phần        |
| DELETE | `/api/students/{id}/`         | Xóa                      |

Validation: `student_code` bắt buộc + unique, `full_name` bắt buộc, `email` hợp lệ.

### Thesis Service — `http://127.0.0.1:8002`

| Method | URL                         | Mô tả                    |
| ------ | --------------------------- | ------------------------ |
| GET    | `/api/theses/`              | Danh sách đề tài         |
| GET    | `/api/theses/?search=web`   | Tìm kiếm                 |
| POST   | `/api/theses/`              | Tạo đề tài               |
| GET    | `/api/theses/{id}/`         | Chi tiết                 |
| PUT    | `/api/theses/{id}/`         | Cập nhật toàn bộ         |
| PATCH  | `/api/theses/{id}/`         | Cập nhật một phần        |
| DELETE | `/api/theses/{id}/`         | Xóa                      |

Validation: `thesis_code` unique, `title` bắt buộc, `max_students > 0`. `status` là `OPEN` (mặc định) hoặc `CLOSED`.

### Registration Service — `http://127.0.0.1:8003`

| Method | URL                                   | Mô tả                                         |
| ------ | ------------------------------------- | --------------------------------------------- |
| GET    | `/api/registrations/`                 | Danh sách đăng ký                             |
| GET    | `/api/registrations/?student_id=1`    | Lọc theo sinh viên                            |
| GET    | `/api/registrations/?thesis_id=1`     | Lọc theo đề tài                               |
| GET    | `/api/registrations/?status=APPROVED` | Lọc theo trạng thái                           |
| POST   | `/api/registrations/`                 | Đăng ký (★ gọi Student + Thesis Service)      |
| GET    | `/api/registrations/{id}/`            | Chi tiết                                      |
| PUT    | `/api/registrations/{id}/`            | Đổi trạng thái `{"status": "APPROVED"}`       |
| PATCH  | `/api/registrations/{id}/`            | Đổi trạng thái `{"status": "REJECTED"}`       |
| DELETE | `/api/registrations/{id}/`            | Hủy đăng ký                                   |

`status`: `PENDING` (mặc định khi tạo), `APPROVED`, `REJECTED`. Sau khi tạo, chỉ được đổi `status`; muốn đổi sinh viên/đề tài thì xóa và đăng ký lại.

## 10. Swagger URL

| Service              | Swagger UI                         |
| -------------------- | ---------------------------------- |
| Student Service      | http://127.0.0.1:8001/api/docs/    |
| Thesis Service       | http://127.0.0.1:8002/api/docs/    |
| Registration Service | http://127.0.0.1:8003/api/docs/    |

(File OpenAPI dạng YAML: `/api/schema/`.)

Cách dùng: mở API → **Try it out** → nhập body → **Execute**.

## 11. Demo CRUD

**1. Tạo sinh viên** — Swagger 8001 → `POST /api/students/`:

```json
{
  "student_code": "SV004",
  "full_name": "Phạm Thị Dung",
  "email": "dung.pham@student.edu.vn",
  "class_name": "CNTT2",
  "major": "Công nghệ thông tin"
}
```
→ `201 Created`, ghi lại `id` (ví dụ `4`).

Thử lỗi validation (trùng mã, email sai):
```json
{ "student_code": "SV001", "full_name": "Test", "email": "abc" }
```
→ `400` `{"student_code": ["student with this student code already exists."], "email": ["Enter a valid email address."]}`

**2. Tìm kiếm** — `GET /api/students/?search=Nguyen` → ra "Nguyễn Văn An" (tìm không dấu nhờ hàm `unaccent` của PostgreSQL).

**3. Sửa / xóa** — `PATCH /api/students/4/` với `{"class_name": "CNTT3"}`; `DELETE /api/students/4/` → `204`.

**4. Tạo đề tài** — Swagger 8002 → `POST /api/theses/`:

```json
{
  "thesis_code": "DT004",
  "title": "Ứng dụng web bán hàng",
  "description": "Website thương mại điện tử",
  "supervisor": "TS. Phạm Minh Tuấn",
  "max_students": 2
}
```
→ `201`, `status` mặc định `OPEN`. Thử `"max_students": 0` → `400`.

## 12. Demo Registration Service gọi Student/Thesis Service

Mở Swagger 8003 → `POST /api/registrations/`. Đặt 3 cửa sổ terminal cạnh nhau để giảng viên thấy **log request xuất hiện ở terminal 8001 và 8002** mỗi lần gọi API đăng ký.

Luồng xử lý khi gọi `POST /api/registrations/` với `{"student_id": 3, "thesis_id": 1}`:

```
Client ── POST /api/registrations/ ──► Registration Service (8003)
                                            │
     Kiểm tra trùng trong registration_db   │
                                            │ Bước 1: GET http://127.0.0.1:8001/api/students/3/
                                            ├──────────────────────────────► Student Service
                                            │ ◄────────── 200 {...} / 404
                                            │ Bước 2: GET http://127.0.0.1:8002/api/theses/1/
                                            ├──────────────────────────────► Thesis Service
                                            │ ◄────────── 200 {"status": "OPEN", "max_students": 3, ...}
                                            │ Bước 3: thesis.status == "OPEN" ?
                                            │ Bước 4: số đăng ký (≠ REJECTED) của thesis < max_students ?
                                            │ Bước 5: lưu vào registration_db
Client ◄── 201 Created ─────────────────────┘
```

Kịch bản demo với dữ liệu mẫu:

| # | Body                                   | Kết quả mong đợi                                                       |
| - | -------------------------------------- | ---------------------------------------------------------------------- |
| 1 | `{"student_id": 3, "thesis_id": 1}`    | `201` — đăng ký thành công, `status: PENDING`                          |
| 2 | `{"student_id": 1, "thesis_id": 1}`    | `400` `{"error": "Student has already registered for this thesis"}`    |
| 3 | `{"student_id": 999, "thesis_id": 1}`  | `400` `{"error": "Student does not exist"}`                            |
| 4 | `{"student_id": 1, "thesis_id": 999}`  | `400` `{"error": "Thesis does not exist"}`                             |
| 5 | `{"student_id": 1, "thesis_id": 3}`    | `400` `{"error": "Thesis is closed"}`                                  |
| 6 | `{"student_id": 1, "thesis_id": 2}`    | `400` `{"error": "Thesis has reached maximum students"}` (DT002 tối đa 1) |
| 7 | Tắt Student Service (Ctrl+C ở terminal 8001), gửi `{"student_id": 2, "thesis_id": 2}` | `503` `{"error": "Student Service unavailable"}` (bật lại 8001 sau khi demo) |

Sau đó:
- Duyệt đăng ký: `PATCH /api/registrations/2/` với `{"status": "APPROVED"}`.
- Lọc: `GET /api/registrations/?thesis_id=1`, `?student_id=1`, `?status=APPROVED`.

**Demo "đổi bên trong, giữ API":** đóng đề tài ở Thesis Service bằng `PATCH http://127.0.0.1:8002/api/theses/1/` `{"status": "CLOSED"}` → đăng ký mới vào đề tài 1 lập tức bị từ chối `Thesis is closed`, mà Registration Service không hề đọc `thesis_db`.

## 13. Giải thích: Tại sao đây là SOA?

1. **Mỗi service một trách nhiệm (độc lập về nghiệp vụ)**
   - Student Service chịu trách nhiệm quản lý sinh viên.
   - Thesis Service chịu trách nhiệm quản lý đề tài.
   - Registration Service chịu trách nhiệm quản lý đăng ký.

2. **Độc lập về triển khai và dữ liệu**
   - 3 Django project riêng, 3 process riêng, 3 port riêng (8001/8002/8003).
   - 3 database riêng. Registration Service **không** kết nối `student_db` hay `thesis_db` (xem `DATABASES` trong `registration-service/config/settings.py`).
   - `student_id`, `thesis_id` trong bảng `dangky` **không phải ForeignKey** — vì dữ liệu nằm ở database khác (`registrations/models.py`).

3. **Giao tiếp qua giao thức chuẩn HTTP/REST + JSON**
   - Registration Service chỉ biết **URL** của service khác (cấu hình trong `.env`), gọi bằng `requests.get(...)` trong `registrations/services/external_api.py`.
   - Mọi HTTP call đều có **timeout**; nếu service kia chết → trả `503 Service Unavailable` thay vì treo hoặc lỗi 500.

4. **Loose coupling — điểm quan trọng nhất**
   - Registration Service chỉ phụ thuộc vào **API contract** (`GET /api/students/{id}/` trả JSON có `id`; `GET /api/theses/{id}/` trả JSON có `status`, `max_students`).
   - Nếu thay đổi implementation bên trong Student Service (đổi tên bảng, đổi cách lưu, thêm cột, thậm chí viết lại bằng ngôn ngữ khác) **nhưng giữ nguyên API**, thì Registration Service **không cần sửa một dòng code nào**.
   - Nếu đổi địa chỉ server, chỉ cần sửa `STUDENT_SERVICE_URL` trong `.env`.

5. **Khả năng tái sử dụng**
   - `GET /api/students/{id}/` không được viết riêng cho Registration Service: bất kỳ hệ thống nào khác (chấm điểm, học phí, thư viện...) cũng dùng lại được Student Service qua cùng API.
   - Trong Registration Service, các hàm `get_student()`, `get_thesis()` trong `external_api.py` được tái sử dụng ở API tạo đăng ký, API cập nhật trạng thái và lệnh `seed_data`.
   - **Web Portal** là ví dụ thực tế cho việc tái sử dụng: giao diện web được thêm vào sau mà **không phải sửa một dòng code nào** của 3 service. Nó dùng lại đúng các API đã có, giống như Swagger hay Registration Service đang dùng.

## Câu hỏi giảng viên hay hỏi — trả lời nhanh

| Câu hỏi | Trả lời / chỉ vào file |
| ------- | ---------------------- |
| Code gọi service khác nằm ở đâu? | `registration-service/registrations/services/external_api.py` |
| Luồng kiểm tra 5 bước ở đâu? | `check_registration_rules()` trong `registrations/views.py` |
| Sao không dùng ForeignKey? | Student/Thesis ở database khác; DB không thể ràng buộc khóa ngoại xuyên database → kiểm tra bằng REST API |
| Chống đăng ký trùng thế nào? | Kiểm tra trong view + `UniqueConstraint(student_id, thesis_id)` ở database |
| Service khác chết thì sao? | `requests` có timeout, bắt `RequestException` → `503 {"error": "... unavailable"}` |
| Test không cần chạy service khác? | Đúng — `tests.py` mock `requests.get` bằng `unittest.mock.patch` |
| Mật khẩu DB để đâu? | File `.env` (không commit), code đọc qua `os.getenv` |
