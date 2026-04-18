# Phát triển Tính năng Cốt lõi: Auth thật, Multi-User Sessions, và Stable Job IDs

Tài liệu này theo dõi tiến độ nâng cấp ứng dụng từ trạng thái "Demo Single-User" lên "Multi-User / Production-Ready", bao gồm việc hoàn thiện hệ thống Session, Database và Giao diện người dùng.

## 1. Trạng thái Hoàn thành (Đã làm)

### Backend (`app.py` & Khung logic)
- [x] **Session Multi-User:** Đã tạo hệ thống lưu trữ in-memory phân tách người dùng bằng ID UUID (`user_sessions_store`). Ngăn chặn tình trạng xung đột dữ liệu CV giữa nhiều người dùng khác nhau.
- [x] **Database Authentication:** Đã gỡ bỏ bản nháp cơ sở dữ liệu `users.json` và thay thế hoàn toàn bằng **SQLite3 Database (`data/app.db`)**. Cơ chế này xử lý tốt vấn đề lưu trữ đồng thời và tính toàn vẹn dữ liệu. Đã sử dụng mã hóa `werkzeug.security` (PBKDF2 SHA256) cho Mật khẩu.
- [x] **Memory Management:** Đã áp dụng tính năng tự dọn dẹp các Session cũ (chỉ được lưu lại tối đa 100 người hoạt động song song hoặc bị hủy sau 24h) qua hàm `cleanup_stale_sessions()`. Giải quyết triệt để rủi ro tràn RAM của Server. 
- [x] **Validation (Kiểm duyệt):** Backend đã chặn gửi Register nếu định dạng email không đúng chuẩn (xác minh bằng Regex) hoặc mật khẩu dưới 6 ký tự.
- [x] **Stable Job IDs:** Hệ thống Route chi tiết công việc `/job/<job_id>` đã được chuẩn hóa để gọi tham chiếu string (ví dụ: `JobPosting::DS_001`), không còn gọi bằng Index số nguyên gây lỗi index crash khi refresh trình duyệt.

### Frontend (`main.js` & Giao diện UI)
- [x] **Route Auth Status:** API `/api/auth-status` đã tích hợp để JS tự động fetch và đồng bộ trạng thái Login mỗi khi F5 hoặc load trang mới.
- [x] **Fix Bug Form HTML:** Đã sửa chữa biểu mẫu Đăng nhập / Đăng ký hiện tại (`modals.html`). Thêm thuộc tính `name=""` để `FormData` của JS bắt được trọn vẹn JSON payload. Bổ sung input Xác nhận mật khẩu (`confirm_password`) vào modal đăng ký.
- [x] **Fix Bug Tên người dùng:** Gỡ bỏ chữ cứng (Hard-coded) "John Doe". Giao diện trên góc phải tự động đọc chữ cái đầu trong tên để vẽ Icon (`user-avatar-display`) và thay đổi Text tên tương ứng `user-name-display` chuẩn.
- [x] **Fix Bug Sai URL Layout:** Khắc phục lỗi `404 Not Found` trên màn hình Dashboard do sai sót chính tả dấu gạch dưới khi chuyển hướng đến thẻ Kỹ năng (`/skills-page`).

---

## 2. Những phần còn thiếu (Cần làm tiếp theo)

Hệ thống cơ bản đã hoàn thiện vững chắc, nhưng có thể mở rộng bằng các tính năng này để tăng tính mượt mà cho trải nghiệm:

### Trải nghiệm người dùng (Frontend UI/UX)
- [ ] **Validation Feedback ngay trên Khung Text:** Thay vì chỉ hiện Pop-up Thông báo Toast nếu sai định dạng, màn hình có thể hiện *viền đỏ / text cảnh báo nhỏ* ngay phía dưới những ô người dùng nhập sai (cung cấp trải nghiệm Real-time Validation UI tiêu chuẩn).
- [ ] **Tính năng Forgot Password (Quên mật khẩu):** Màn hình hiện tại chưa có flow Reset Password. Cột mốc tiếp theo có thể vẽ thêm 1 Pop-up Modal, đi kèm Route `/api/forgot-password` xử lý Email.

### Nâng cấp Kiến trúc Server (Dài hạn)
- [ ] **Data Persistence cho Session Store:** Mặc dù Memory leak đã được giải quyết, nhưng hiện tại session mạng (`current_G` và `cv_vec`) vẫn cắm vào RAM cục bộ. Khi Restart lại con Server (`Ctrl+C` khởi động lại FLASK), toàn bộ thông tin kết quả đang làm việc của User sẽ bị Reset sạch (dù giữ nguyên Auth login). Giải pháp là thiết lập `Redis` hoặc sử dụng bảng `Sessions` để Pickles Serializer lại toàn bộ Dictionary lưu vào DB hòng giữ nguyên Cache CV.
- [ ] **Upload CV Size limit Handling:** Hiện backend cho max content=100MB qua config nhưng chưa có thiết lập Frontend báo lỗi thân thiện ngay mặt giao diện nếu người ta cố tình kéo thả File PDF vượt kích cỡ nặng vào.
