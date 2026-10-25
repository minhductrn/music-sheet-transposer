# Music Sheet Transposer

**Giao diện mặc định: `frontend-v2/`.** Các lệnh chạy, build và kiểm tra tại thư mục gốc đều dùng frontend-v2. `frontend/` được giữ làm tham chiếu lịch sử; không bị xóa hoặc thay tên.

Bản đã nghiệm thu hỗ trợ MusicXML thật: chỉnh sửa nốt/lời/tie/slur/nhóm nốt, đổi Concert Key, lưu Concert, tạo và chỉnh sửa bản Alto/Soprano/Tenor độc lập, xuất MusicXML/PDF. Original Source chỉ đọc; người dùng chỉnh sửa trong Working Score.

**Nhập PDF/hình ảnh và OMR thật chưa thuộc luồng frontend-v2 đã nghiệm thu.** Demo vẫn là mô phỏng. Các module OMR lịch sử trong backend không có nghĩa tính năng đó đã được tích hợp hoặc nghiệm thu trong giao diện mới.

## Chạy ứng dụng để phát triển

Dùng Ubuntu WSL, Node 24 và Python cùng môi trường backend hiện có. Với bản clone mới, tạo môi trường backend một lần:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ..
```

Từ thư mục gốc, terminal thứ nhất chạy backend:

```bash
cd backend
.venv/bin/python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal thứ hai, ở thư mục gốc:

```bash
npm run setup:frontend
npm run dev
```

`setup:frontend` chỉ cần khi cài mới hoặc cập nhật dependencies. `npm start` cũng chạy giao diện phát triển v2. Mở **http://localhost:5174**. Giữ cả hai terminal trong lúc sử dụng; Ctrl+C để dừng. Nếu cổng đã có phiên đang chạy, dùng phiên đó hoặc dừng nó trước, không khởi chạy chồng lên.

Mặc định frontend proxy `/api` tới `http://127.0.0.1:8000`. Để đổi địa chỉ backend:

```bash
AI_SDF_BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

Không dùng `VITE_BACKEND_URL` của giao diện cũ cho frontend-v2.

## Build và kiểm tra mặc định

Chạy từ thư mục gốc:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

Build tạo kết quả tại **`frontend-v2/dist/`**. Không dùng `frontend/dist/` cho giao diện mặc định mới. Đây là build giao diện; để chạy gói có cả API, dùng Task 03 bên dưới.

`npm run test:e2e` dùng bộ Playwright của frontend-v2 và tự khởi động máy chủ trên cổng 5174/8812; cần các cổng đó đang trống. Cấu hình trình duyệt hiện có đường dẫn Firefox của máy WSL đã kiểm thử; máy khác cần điều chỉnh đường dẫn cục bộ trước khi chạy. Không cần Audiveris hoặc AI Agent cho luồng MusicXML này.

## Bản chạy thử độc lập — Task 03 đã nghiệm thu

Bản đóng gói dùng cổng **5180**, có frontend đã build và thư viện backend đi kèm, chạy không cần Node, Codex hoặc terminal phát triển. Gói dành cho Ubuntu WSL/Python ABI đã ghi trong manifest, chưa phải bộ cài Windows hoặc triển khai production.

- [Hướng dẫn người dùng](pilot-release/USER_GUIDE_VI.md)
- [Cách đóng gói lại từ checkpoint đã nghiệm thu](pilot-release/README.md)
- [Báo cáo nghiệm thu Task 03](pilot-release/TASK_03_REPORT.md)
- [Checkpoint UX v2](frontend-v2/RELEASE_CHECKPOINT.md)

Archive/runtime và bằng chứng có dữ liệu riêng tư chỉ lưu local, không đưa vào Git. Clone repository cung cấp mã nguồn và builder; không tự có sẵn gói runtime đã tạo trên máy thử nghiệm.

## Lưu và mở lại dữ liệu

Dùng Save As để bảo vệ file gốc. Với trình duyệt tải file xuống, chỉ xác nhận đã giữ file sau khi kiểm tra file trên máy. Lưu Concert trước khi tạo bản nhạc cụ; lưu từng bản nhạc cụ cần giữ. Mở lại bằng file MusicXML đã lưu. Các phiên bộ nhớ, Undo/Redo và biến thể chưa lưu không tự phục hồi sau khi đóng ứng dụng.

## Cấu trúc và lịch sử

| Thư mục | Vai trò |
| --- | --- |
| `frontend-v2/` | Giao diện mặc định đã nghiệm thu |
| `backend/` | API MusicXML/review/transposition; giữ nguyên trong thay đổi mặc định này |
| `pilot-release/` | Builder, launcher và hướng dẫn bản chạy độc lập |
| `frontend/` | Giao diện cũ, giữ nguyên để tham chiếu |

[README lịch sử](README_LEGACY.md) giữ tài liệu cũ về frontend/OMR và các benchmark; không dùng các trạng thái lịch sử đó để suy ra phạm vi nghiệm thu v2 hiện tại. Không có cấu hình CI/hosting triển khai tự động trong repository tại thời điểm chuyển mặc định này; chưa thực hiện production deployment.

Quy trình quản trị: [Product Constitution](PRODUCT_CONSTITUTION.md), [Acceptance Criteria](ACCEPTANCE_CRITERIA.md), và [báo cáo chuyển giao diện mặc định](DEFAULT_FRONTEND_REPORT.md).
