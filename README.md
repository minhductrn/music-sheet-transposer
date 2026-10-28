# Music Sheet Transposer

Ứng dụng cục bộ để nhập bản nhạc, chỉnh sửa trực tiếp, đổi giọng Concert và tạo bản viết cho saxophone. **Giao diện mặc định là `frontend-v2/`**; `frontend/` được giữ làm tham chiếu lịch sử.

## Trạng thái hiện tại

**Task 04 đã được Product Owner nghiệm thu ngày 2026-10-27**, trong phạm vi và giới hạn ghi tại [báo cáo Task 04](frontend-v2/TASK_04_REPORT.md). Checkpoint mã nguồn đã đồng bộ GitHub: [`56e798e`](https://github.com/minhductrn/music-sheet-transposer/commit/56e798ecae8ac3c17317b421f873f59db4c8cbcc).

- Nhập MusicXML thật hoặc PDF/PNG/JPEG qua OMR để tạo bản nháp.
- Original Source bên trái chỉ đọc; người dùng quyết định mọi chỉnh sửa trong Working Score bên phải. Edit Only giữ cùng công cụ và chỉ ẩn bản gốc.
- Chỉnh nốt, cao độ, trường độ, dấu hóa, dấu lặng, dot/double dot, bè, ô nhịp, nhóm nốt và các tuplet được hỗ trợ; chọn nhiều nốt bằng chuột.
- Thêm/sửa lời theo nốt và nhiều verse; chỉnh văn bản, hợp âm, tie/slur và xóa các đối tượng OCR được hỗ trợ trực tiếp trên bản nhạc.
- Chuyển Concert Key, giữ các đoạn đổi giọng; xác nhận giọng gốc khi thiếu thông tin đầu bài. **Cùng giọng + Down** hạ toàn bài một quãng tám; cùng giọng + Up giữ nguyên cao độ. Có Undo/Redo.
- Tạo và chỉnh sửa bản Alto/Soprano/Tenor độc lập. Mặc định bản viết dễ đọc: Alto −3 bán âm, Soprano +2, Tenor +2 so với Concert. Tenor theo lựa chọn đã nghiệm thu viết giống Soprano và khi chơi trên Tenor B♭ sẽ vang thấp hơn Concert một quãng tám; đây là lựa chọn âm vực, không phải quy tắc Tenor chuẩn +14 bán âm.
- Lưu/mở lại MusicXML và xuất PDF A4 đứng, khoảng cách khuôn/lời/nốt gọn; bài dài tự chia nhiều trang.
- Fit vừa chiều ngang, zoom và cuộn độc lập; Home cho phép lưu, tiếp tục sửa hoặc bỏ thay đổi chưa lưu để nhập bài khác.

OMR có thể nhận sai hoặc thiếu. Bản nháp cần được người dùng đối chiếu và chỉnh sửa; ứng dụng không tự sáng tác phần còn thiếu. Không có AI Agent, LLM API hoặc Docker trong luồng Task 04.

## Chạy để phát triển

Dùng Ubuntu WSL, Node 24 và Python phù hợp với dependencies backend. Với clone mới, chuẩn bị backend một lần:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ..
```

Terminal thứ nhất chạy API:

```bash
cd backend
.venv/bin/python -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal thứ hai, từ thư mục gốc repository:

```bash
npm run setup:frontend
npm run dev
```

Mở **http://localhost:5174**. `setup:frontend` chỉ cần khi cài mới hoặc cập nhật dependencies; `npm start` cũng chạy giao diện phát triển. Giữ hai terminal khi sử dụng, Ctrl+C để dừng. Không khởi chạy chồng lên phiên đang dùng cùng cổng.

Frontend mặc định proxy `/api` tới `http://127.0.0.1:8000`. Để đổi backend:

```bash
AI_SDF_BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

Không dùng `VITE_BACKEND_URL` của giao diện cũ cho frontend-v2.

### Yêu cầu riêng cho OMR

Luồng PDF/hình ảnh cần Java, Audiveris và dữ liệu OCR phù hợp đã có trên máy. Gói ứng dụng không chứa Java/Audiveris/mô hình OCR và không tự tải chúng. Có thể cấu hình `AUDIVERIS_EXECUTABLE` và `AUDIVERIS_TESSDATA_PATH`; xem [hướng dẫn Task 04](pilot-release/TASK_04_GUIDE_VI.md). Luồng nhập/chỉnh sửa MusicXML không cần Audiveris. Khi công cụ OMR và mô hình đã sẵn có cục bộ, nhận diện không cần dịch vụ AI trực tuyến.

## Bản chạy độc lập đã nghiệm thu

Gói hiện tại: **`music-sheet-transposer-task04-accepted-2026-10-27.tar.gz`**. Gói và runtime được giữ cục bộ; clone GitHub không tự có sẵn archive.

Giải nén vào thư mục mới, rồi chạy trong Ubuntu WSL:

```bash
python3 -B /duong-dan-goi/start.py --check
python3 -B /duong-dan-goi/start.py --port 5180
```

Thay `/duong-dan-goi` bằng đường dẫn thư mục vừa giải nén. Mở **http://localhost:5180**; chọn cổng khác bằng `--port` nếu đang có phiên sử dụng. Giữ terminal và nhấn Ctrl+C khi muốn dừng.

Gói chứa frontend đã build và thư viện Python, cần Python hệ thống đúng ABI trong `manifest.json`. Không cần Node, Codex hay máy chủ phát triển khi chạy. OMR vẫn cần bộ công cụ cục bộ nêu trên. Đây là bản thử nghiệm local, chưa phải bộ cài Windows hoặc triển khai production.

- [Hướng dẫn Task 04 và các giới hạn](pilot-release/TASK_04_GUIDE_VI.md)
- [Báo cáo triển khai, kiểm chứng và nghiệm thu](frontend-v2/TASK_04_REPORT.md)
- [Hướng dẫn Task 03 trước đây](pilot-release/USER_GUIDE_VI.md) và [cách đóng gói Task 03](pilot-release/README.md) là tài liệu lịch sử, không thay thế hướng dẫn Task 04.

Builder hiện tại là `pilot-release/build_task04.py`. Trên máy đóng gói đã có dependencies và runtime Tenor được bảo vệ, có thể chạy từ repository:

```bash
python3 -B pilot-release/build_task04.py --accepted --output /duong-dan-tuyet-doi/thu-muc-goi-moi
```

Builder từ chối ghi đè đầu ra cũ. Nó cần cache runtime Tenor cục bộ không được phân phối trong Git; clone mới chưa đủ để tự tạo gói. Chỉ dùng `--accepted` cho phạm vi đã được Product Owner nghiệm thu.

## Lưu và mở lại

MusicXML là dữ liệu để chỉnh sửa tiếp; PDF là bản in. Dùng Save As để bảo vệ file gốc. Với trình duyệt tải file xuống, chỉ xác nhận đã giữ file khi đã kiểm tra đúng tên và thư mục; chú ý hậu tố `(1)`, `(2)`.

- Bản OMR cần đối chiếu bản gốc, xác nhận so sánh rồi lưu; sửa tiếp sẽ yêu cầu xác nhận lại.
- Bản Concert đã chỉnh sửa cần lưu trước khi tạo Instrument Scores. MusicXML nhập có giọng đầu bài rõ ràng và chưa thay đổi có thể chuyển sang Instrument Scores ngay.
- Lưu riêng từng bản nhạc cụ cần giữ. Khi mở lại bản written score, nó là tài liệu độc lập; không transpose nhạc cụ lần nữa nếu không có chủ ý.
- Phiên bộ nhớ, Undo/Redo và các biến thể chưa lưu không tự phục hồi sau khi đóng/khởi động lại. Các tệp đã lưu không bị Home xóa.

## Kiểm tra và build

Từ thư mục gốc:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

Build giao diện nằm tại **`frontend-v2/dist/`**. Để kiểm tra backend:

```bash
cd backend
.venv/bin/python -B -m pytest -q --ignore=tests/music/test_recognition_benchmark.py
```

Checkpoint Task 04 ghi nhận **1.122 kiểm thử backend đạt, 3 bỏ qua; 55 kiểm thử frontend đạt**, lint/typecheck/build đạt. Kiểm tra browser có phạm vi riêng được ghi trong báo cáo; các con số này không khẳng định độ chính xác OMR tuyệt đối.

`npm run test:e2e` dùng Playwright và cần các cổng 5174/8812 trống. Cấu hình hiện có đường dẫn Firefox của máy WSL đã kiểm thử; máy khác cần điều chỉnh. Một số kiểm thử dùng mẫu riêng/bằng chứng cục bộ không được công bố; xem điều kiện bỏ qua và đường dẫn trong từng kiểm thử. Không chạy đè lên phiên đang chứa chỉnh sửa chưa lưu.

## Giới hạn và dữ liệu riêng

- Không bảo đảm nhận diện đúng mọi ký hiệu, font cũ, bè hoặc lời; không có tỷ lệ chính xác được chứng nhận cho mọi PDF.
- PDF mã hóa chưa được hỗ trợ. Mẫu có nhiều score đầu ra không được tự chọn hoặc tự gộp.
- Chỉnh sửa và tuplet có phạm vi được mô tả trong báo cáo; chưa tương đương toàn bộ MuseScore/Symphony Pro. Stage 2 còn giới hạn single-part; Add measure còn giới hạn cấu trúc single-part/single-staff.
- Một số cách ghi chuyển giọng vượt quá 7 dấu hóa cần người dùng chọn cách ghi tương đương được hỗ trợ. Không tự đổi lựa chọn âm nhạc của người dùng.
- PDF dài vẫn dùng nhiều trang; không ép mọi bản nhạc vào một trang A4.
- PDF/MusicXML cá nhân, runtime, archive và bằng chứng riêng chỉ lưu local, không đưa vào Git. Các thay đổi legacy ngoài phạm vi vẫn được giữ riêng.

## Cấu trúc và quản trị

| Thư mục | Vai trò |
| --- | --- |
| `frontend-v2/` | Giao diện mặc định, báo cáo và kiểm thử Task 04 |
| `backend/` | API nhận diện, review/chỉnh sửa và chuyển giọng MusicXML |
| `pilot-release/` | Builder, launcher và hướng dẫn bản chạy độc lập |
| `frontend/` | Giao diện cũ để tham chiếu |

[README lịch sử](README_LEGACY.md) lưu tài liệu cũ; không dùng trạng thái lịch sử để suy ra phạm vi hiện tại. Checkpoint GitHub là mã nguồn, không đồng nghĩa production deployment.

Quy trình quản trị: [Product Constitution](PRODUCT_CONSTITUTION.md), [Acceptance Criteria](ACCEPTANCE_CRITERIA.md). Product Owner giữ quyền nghiệm thu; kiểm thử PASS không thay thế xác nhận đó.
