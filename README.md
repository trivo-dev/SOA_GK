# Hệ thống quản lý đồ án tốt nghiệp theo kiến trúc SOA

Bài thực hành giữa kỳ môn **Công nghệ phần mềm** — Django, Django REST Framework, PostgreSQL.

## 1. Giới thiệu

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
                                    │  gọi REST API của cả 3 service
                ┌───────────────────┼─────────────────────────┐
                │      (hoặc Swagger UI / Postman / curl)     │
                ▼                   ▼                         ▼
     ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────────┐
     │ Student Service  │ │  Thesis Service  │ │  Registration Service   │
     │   :8001          │ │   :8002          │ │   :8003                 │
     │ /api/students/   │ │ /api/theses/     │ │ /api/registrations/     │
     └────────┬─────────┘ └────────┬─────────┘ └──┬───────────┬──────────┘
              │                    │              │           │
              │  ◄── HTTP GET /api/students/{id}/ ┘           │
              │                    │  ◄── HTTP GET /api/theses/{id}/
              ▼                    ▼                          ▼
         student_db           thesis_db               registration_db
```

- Mỗi service là **một Django project riêng**, chạy **một process riêng**, trên **một port riêng**.
- Mỗi service **chỉ kết nối database của chính nó**.
- Registration Service **không có ForeignKey** tới Student/Thesis: bảng `dangky` chỉ lưu `student_id`, `thesis_id` (số nguyên). Việc kiểm tra sinh viên/đề tài có tồn tại hay không được thực hiện bằng cách **gọi REST API** của service tương ứng.
- Web Portal **không có database**, mọi dữ liệu đều lấy qua REST API.

## 3. Công nghệ sử dụng

- Python 3.12+ (đã chạy với Python 3.14)
- Django, Django REST Framework
- PostgreSQL (driver `psycopg` 3)
- `requests` — gọi HTTP giữa các service
- `drf-spectacular` — sinh tài liệu OpenAPI và Swagger UI
- `python-dotenv` — đọc cấu hình từ file `.env`
- Bootstrap 5 — giao diện Web Portal

## 4. Cấu trúc project

```
SOA_GK/
├── README.md
├── run_all.bat                       # Mở 4 cửa sổ chạy 4 service cùng lúc (Windows)
│
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
│   └── theses/                       # Cấu trúc giống students/
│
├── registration-service/             # Port 8003 - registration_db
│   ├── .env.example                  # Có thêm STUDENT_SERVICE_URL, THESIS_SERVICE_URL
│   └── registrations/
│       ├── models.py                 # Registration: student_id, thesis_id không phải ForeignKey
│       ├── serializers.py
│       ├── views.py                  # Luồng nghiệp vụ đăng ký
│       ├── urls.py
│       ├── services/
│       │   └── external_api.py       # Toàn bộ code gọi HTTP sang Student/Thesis Service
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

## 5. Cài đặt

### 5.1. Lấy mã nguồn và cài thư viện

```powershell
git clone https://github.com/trivo-dev/SOA_GK.git
cd SOA_GK
python -m venv .venv
.venv\Scripts\activate
pip install -r student-service\requirements.txt -r thesis-service\requirements.txt -r registration-service\requirements.txt -r web-portal\requirements.txt
```

> Nếu PowerShell chặn lệnh `activate`, chạy `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` một lần.

### 5.2. Tạo database

Sử dụng một PostgreSQL server với 3 database riêng. Dùng `psql` hoặc pgAdmin:

```sql
CREATE DATABASE student_db;
CREATE DATABASE thesis_db;
CREATE DATABASE registration_db;
```

### 5.3. Cấu hình `.env`

Mỗi service đọc cấu hình từ file `.env` của riêng nó; mật khẩu và thông tin database không được ghi trong code. Tạo `.env` từ `.env.example`:

```powershell
copy student-service\.env.example       student-service\.env
copy thesis-service\.env.example        thesis-service\.env
copy registration-service\.env.example  registration-service\.env
copy web-portal\.env.example            web-portal\.env
```

Sau đó sửa `DB_PASSWORD` cho đúng mật khẩu PostgreSQL. Ví dụ `student-service/.env`:

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

> Nên dùng `127.0.0.1` thay vì `localhost`: trên Windows, `localhost` được thử IPv6 trước nên mỗi request chậm thêm khoảng 2 giây.

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

Web Portal không có database nên không cần `migrate`.

## 6. Chạy hệ thống

**Cách nhanh (Windows):** chạy file `run_all.bat`. File này mở 4 cửa sổ, mỗi cửa sổ chạy một service.

**Cách thủ công:** mở 4 terminal (đã `activate` virtualenv):

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

### Dữ liệu mẫu

Sau khi các service đang chạy:

```powershell
cd student-service;      python manage.py seed_data; cd ..
cd thesis-service;       python manage.py seed_data; cd ..
cd registration-service; python manage.py seed_data; cd ..
```

`seed_data` của Registration Service lấy id sinh viên/đề tài thông qua REST API, vì vậy Student Service và Thesis Service phải đang chạy. Lệnh có thể chạy nhiều lần mà không tạo dữ liệu trùng.

| Sinh viên                  | Đề tài                                                      |
| -------------------------- | ----------------------------------------------------------- |
| id=1 SV001 - Nguyễn Văn An | id=1 DT001 - Hệ thống quản lý thư viện (OPEN, tối đa 3)     |
| id=2 SV002 - Trần Văn Bình | id=2 DT002 - Hệ thống đặt sân thể thao (OPEN, tối đa 1)     |
| id=3 SV003 - Lê Văn Cường  | id=3 DT003 - Hệ thống quản lý đồ án tốt nghiệp (CLOSED)     |

| Đăng ký | Sinh viên | Đề tài | Trạng thái |
| ------- | --------- | ------ | ---------- |
| 1       | SV001     | DT001  | APPROVED   |
| 2       | SV002     | DT001  | PENDING    |
| 3       | SV003     | DT002  | APPROVED   |

### Địa chỉ truy cập

| Thành phần                     | URL                             |
| ------------------------------ | ------------------------------- |
| Giao diện web (Web Portal)     | http://127.0.0.1:8000/          |
| Swagger - Student Service      | http://127.0.0.1:8001/api/docs/ |
| Swagger - Thesis Service       | http://127.0.0.1:8002/api/docs/ |
| Swagger - Registration Service | http://127.0.0.1:8003/api/docs/ |

Tài liệu OpenAPI (YAML) của mỗi service: `/api/schema/`.

Web Portal dùng `portal_db` riêng để lưu tài khoản và session Django; dữ liệu nghiệp vụ vẫn được lấy qua REST API của 3 service (`portal/api_client.py`). Ví dụ bảng Đăng ký: lấy danh sách đăng ký từ Registration Service, sau đó lấy tên sinh viên từ Student Service và tên đề tài từ Thesis Service rồi ghép lại để hiển thị. Nếu một service bị tắt, trang vẫn mở được và hiện thông báo "... Service không hoạt động".

## 9. Danh sách API

### Student Service — `http://127.0.0.1:8001`

| Method | URL                            | Mô tả                   |
| ------ | ------------------------------ | ----------------------- |
| GET    | `/api/students/`               | Danh sách sinh viên     |
| GET    | `/api/students/?search=Nguyen` | Tìm kiếm (có/không dấu) |
| POST   | `/api/students/`               | Tạo sinh viên           |
| GET    | `/api/students/{id}/`          | Chi tiết                |
| PUT    | `/api/students/{id}/`          | Cập nhật toàn bộ        |
| PATCH  | `/api/students/{id}/`          | Cập nhật một phần       |
| DELETE | `/api/students/{id}/`          | Xóa                     |

Validation: `student_code` bắt buộc và không trùng, `full_name` bắt buộc, `email` đúng định dạng.

### Thesis Service — `http://127.0.0.1:8002`

| Method | URL                       | Mô tả             |
| ------ | ------------------------- | ----------------- |
| GET    | `/api/theses/`            | Danh sách đề tài  |
| GET    | `/api/theses/?search=web` | Tìm kiếm          |
| POST   | `/api/theses/`            | Tạo đề tài        |
| GET    | `/api/theses/{id}/`       | Chi tiết          |
| PUT    | `/api/theses/{id}/`       | Cập nhật toàn bộ  |
| PATCH  | `/api/theses/{id}/`       | Cập nhật một phần |
| DELETE | `/api/theses/{id}/`       | Xóa               |

Validation: `thesis_code` không trùng, `title` bắt buộc, `max_students > 0`. `status` là `OPEN` (mặc định) hoặc `CLOSED`.

### Registration Service — `http://127.0.0.1:8003`

| Method | URL                                   | Mô tả                                     |
| ------ | ------------------------------------- | ----------------------------------------- |
| GET    | `/api/registrations/`                 | Danh sách đăng ký                         |
| GET    | `/api/registrations/?student_id=1`    | Lọc theo sinh viên                        |
| GET    | `/api/registrations/?thesis_id=1`     | Lọc theo đề tài                           |
| GET    | `/api/registrations/?status=APPROVED` | Lọc theo trạng thái                       |
| POST   | `/api/registrations/`                 | Đăng ký đề tài (gọi Student + Thesis Service) |
| GET    | `/api/registrations/{id}/`            | Chi tiết                                  |
| PUT    | `/api/registrations/{id}/`            | Đổi trạng thái, ví dụ `{"status": "APPROVED"}` |
| PATCH  | `/api/registrations/{id}/`            | Đổi trạng thái, ví dụ `{"status": "REJECTED"}` |
| DELETE | `/api/registrations/{id}/`            | Hủy đăng ký                               |

`status`: `PENDING` (mặc định khi tạo), `APPROVED`, `REJECTED`. Sau khi tạo, chỉ được thay đổi `status`; muốn đổi sinh viên hoặc đề tài thì hủy đăng ký và đăng ký lại.

## 8. Giao diện web (Web Portal)

| Menu      | Chức năng                                                                          |
| --------- | ---------------------------------------------------------------------------------- |
| Dashboard | Tổng số sinh viên, đề tài, đề tài đang mở, đăng ký; bảng "Đề tài gần đây"          |
| Sinh viên | Danh sách, tìm kiếm, thêm, sửa, xóa                                                |
| Đề tài    | Danh sách (kèm số đã đăng ký / tối đa), tìm kiếm, thêm, sửa, xóa                   |
| Đăng ký   | Danh sách, lọc theo sinh viên / đề tài / trạng thái, đăng ký mới, duyệt, từ chối, xóa |
| API Docs  | Trạng thái của 3 service và đường dẫn tới Swagger của từng service                |

Mọi trang đều gọi REST API của 3 service thông qua `portal/api_client.py`. Ví dụ, trang Đăng ký lấy danh sách đăng ký từ Registration Service, lấy tên sinh viên từ Student Service, lấy tên đề tài từ Thesis Service rồi ghép lại để hiển thị. Nếu một service ngừng hoạt động, trang vẫn hiển thị được kèm thông báo "... Service không hoạt động".

## 9. Luồng xử lý đăng ký đề tài

Khi client gọi `POST /api/registrations/` với body `{"student_id": 3, "thesis_id": 1}`:

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
                                            │ Bước 4: số đăng ký (khác REJECTED) < max_students ?
                                            │ Bước 5: lưu vào registration_db
Client ◄── 201 Created ─────────────────────┘
```

Mỗi lần gọi API đăng ký, log request `GET /api/students/...` và `GET /api/theses/...` sẽ xuất hiện ở terminal của Student Service và Thesis Service.

### Các trường hợp kiểm tra (với dữ liệu mẫu)

| # | Body                                  | Kết quả                                                                  |
| - | ------------------------------------- | ------------------------------------------------------------------------ |
| 1 | `{"student_id": 3, "thesis_id": 1}`   | `201` — đăng ký thành công, `status: PENDING`                            |
| 2 | `{"student_id": 1, "thesis_id": 1}`   | `400` `{"error": "Student has already registered for this thesis"}`      |
| 3 | `{"student_id": 999, "thesis_id": 1}` | `400` `{"error": "Student does not exist"}`                              |
| 4 | `{"student_id": 1, "thesis_id": 999}` | `400` `{"error": "Thesis does not exist"}`                               |
| 5 | `{"student_id": 1, "thesis_id": 3}`   | `400` `{"error": "Thesis is closed"}`                                    |
| 6 | `{"student_id": 1, "thesis_id": 2}`   | `400` `{"error": "Thesis has reached maximum students"}` (DT002 tối đa 1) |
| 7 | Tắt Student Service, gửi `{"student_id": 2, "thesis_id": 2}` | `503` `{"error": "Student Service unavailable"}` |

### Ví dụ CRUD

Tạo sinh viên — `POST http://127.0.0.1:8001/api/students/`:

```json
{
  "student_code": "SV004",
  "full_name": "Phạm Thị Dung",
  "email": "dung.pham@student.edu.vn",
  "class_name": "CNTT2",
  "major": "Công nghệ thông tin"
}
```

Kết quả `201 Created`. Nếu gửi mã trùng và email sai, ví dụ `{"student_code": "SV001", "full_name": "Test", "email": "abc"}`, kết quả là `400`:

```json
{
  "student_code": ["student with this student code already exists."],
  "email": ["Enter a valid email address."]
}
```

Tạo đề tài — `POST http://127.0.0.1:8002/api/theses/`:

```json
{
  "thesis_code": "DT004",
  "title": "Ứng dụng web bán hàng",
  "description": "Website thương mại điện tử",
  "supervisor": "TS. Phạm Minh Tuấn",
  "max_students": 2
}
```

Kết quả `201 Created`, `status` mặc định là `OPEN`. Nếu `max_students` bằng `0` thì trả về `400`.

Tìm kiếm `GET /api/students/?search=Nguyen` trả về "Nguyễn Văn An" nhờ hàm `unaccent` của PostgreSQL (tìm kiếm không dấu).

## 10. Chi tiết cài đặt

| Nội dung | Cách thực hiện |
| -------- | -------------- |
| Gọi HTTP sang service khác | Tập trung trong `registration-service/registrations/services/external_api.py`, không viết trực tiếp trong `views.py` |
| Kiểm tra điều kiện đăng ký | Hàm `check_registration_rules()` trong `registration-service/registrations/views.py` |
| Không dùng ForeignKey | Student và Thesis nằm ở database khác, không thể ràng buộc khóa ngoại giữa các database; tính hợp lệ được kiểm tra qua REST API |
| Chống đăng ký trùng | Kiểm tra trong view, kèm `UniqueConstraint(student_id, thesis_id)` ở mức database |
| Service khác ngừng hoạt động | Mọi request có `timeout`; lỗi kết nối/timeout được bắt và trả về `503 {"error": "... unavailable"}` |
| Cấu hình nhạy cảm | Đọc từ `.env` qua `os.getenv`; file `.env` không được đưa lên repository |

## 11. Kiểm thử

Test không cần chạy các service khác: HTTP được giả lập bằng `unittest.mock`, Django tự tạo database test tạm thời.

```powershell
cd student-service;      python manage.py test; cd ..
cd thesis-service;       python manage.py test; cd ..
cd registration-service; python manage.py test; cd ..
cd web-portal;           python manage.py test; cd ..
```

| Service              | Số test | Nội dung chính |
| -------------------- | ------- | -------------- |
| Student Service      | 12      | create, list, detail, update (PUT/PATCH), delete, tìm kiếm, validation |
| Thesis Service       | 11      | create, list, detail, update (PUT/PATCH), delete, tìm kiếm, validation |
| Registration Service | 15      | đăng ký thành công; sinh viên/đề tài không tồn tại; đề tài đã đóng; đăng ký trùng; vượt `max_students`; service ngừng hoạt động (503); CRUD và filter |
| Web Portal           | 6       | hiển thị các trang, ghép dữ liệu từ nhiều service, hiển thị lỗi từ API, service ngừng hoạt động |

## 12. Tại sao đây là kiến trúc SOA?

1. **Mỗi service một trách nhiệm**
   - Student Service chịu trách nhiệm quản lý sinh viên.
   - Thesis Service chịu trách nhiệm quản lý đề tài.
   - Registration Service chịu trách nhiệm quản lý đăng ký.

2. **Độc lập về triển khai và dữ liệu**
   - 3 Django project riêng, 3 process riêng, 3 port riêng (8001/8002/8003).
   - 3 database riêng. Registration Service **không** kết nối `student_db` hay `thesis_db` (xem `DATABASES` trong `registration-service/config/settings.py`).
   - `student_id`, `thesis_id` trong bảng `dangky` **không phải ForeignKey** vì dữ liệu nằm ở database khác.

3. **Giao tiếp qua giao thức chuẩn HTTP/REST + JSON**
   - Registration Service chỉ biết **URL** của các service khác (cấu hình trong `.env`) và gọi bằng `requests.get(...)`.
   - Mọi request đều có timeout; nếu service kia ngừng hoạt động, hệ thống trả về `503 Service Unavailable` thay vì treo hoặc lỗi 500.

4. **Liên kết lỏng (loose coupling)**
   - Registration Service chỉ phụ thuộc vào **API contract**: `GET /api/students/{id}/` trả JSON có `id`; `GET /api/theses/{id}/` trả JSON có `status`, `max_students`.
   - Nếu thay đổi cách cài đặt bên trong Student Service (đổi tên bảng, đổi cách lưu, thêm cột, thậm chí viết lại bằng ngôn ngữ khác) **nhưng giữ nguyên API**, Registration Service **không cần thay đổi**.
   - Nếu đổi địa chỉ server, chỉ cần sửa `STUDENT_SERVICE_URL` trong `.env`.
   - Ví dụ: đóng đề tài ở Thesis Service bằng `PATCH /api/theses/1/` với `{"status": "CLOSED"}`, các đăng ký mới vào đề tài này lập tức bị từ chối (`Thesis is closed`) dù Registration Service không đọc `thesis_db`.

5. **Khả năng tái sử dụng**
   - `GET /api/students/{id}/` không được viết riêng cho Registration Service; các hệ thống khác (chấm điểm, học phí, thư viện...) cũng có thể dùng lại Student Service qua cùng API.
   - Các hàm `get_student()`, `get_thesis()` trong `external_api.py` được dùng lại ở API tạo đăng ký, API cập nhật trạng thái và lệnh `seed_data`.
   - **Web Portal** được xây dựng sau mà **không phải sửa code của 3 service**: nó sử dụng lại đúng các API đã có, giống như Swagger UI và Registration Service.
