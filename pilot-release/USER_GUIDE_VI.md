# Music Sheet Transposer — Bản chạy thử độc lập Task 03

## Khởi động và dừng

Bản này dành cho Ubuntu WSL, Linux x86_64, Python 3.14 cùng ABI ghi trong manifest.json. Thư viện Python và giao diện đã build nằm trong gói; không cần Node, npm, Internet, Codex hay hai terminal phát triển khi chạy. Python hệ thống vẫn phải có sẵn; đây không phải bộ cài Windows độc lập.

Giải nén gói vào một thư mục mới. Trong Ubuntu chạy:

    python3 -B /duong-dan-goi/start.py

Mở http://localhost:5180 trong trình duyệt Windows. Có thể dùng PowerShell tại thư mục gói: `powershell -ExecutionPolicy Bypass -File ./Start-Pilot.ps1`. Giữ cửa sổ này khi sử dụng; nhấn Ctrl+C để dừng. Nếu cổng đang dùng, thêm `--port 5181`. Không dùng cổng 5174 của phiên phát triển hiện tại. `python3 -B /duong-dan-goi/start.py --check` kiểm tra toàn vẹn gói mà không khởi động ứng dụng.

## Làm việc và lưu Concert

1. Open MusicXML, chọn file .musicxml/.xml. Original Source bên trái chỉ đọc; chỉnh sửa ở Working Score bên phải.
2. Thực hiện chỉnh sửa, đổi Concert Key nếu cần. Dùng Fit để vừa chiều ngang và cuộn dọc xem tiếp.
3. Dùng Save As để đặt tên bản mới, bảo vệ bản gốc. Trình duyệt hỗ trợ sẽ mở hộp thoại lưu; Firefox tải file xuống, sau đó chỉ bấm “I retained the downloaded file” khi đã giữ được file.
4. Kiểm tra đúng thư mục và tên file đã lưu trước khi đóng. Nếu trình duyệt tự thêm (1), (2), hãy dùng đúng bản mới nhất.

## Bản nhạc cụ và mở lại sau khi đóng

Chỉ tạo Instrument Scores từ Concert đã lưu và không còn chỉnh sửa chưa lưu. Chọn Alto/Soprano/Tenor và Up/Down. Bên trái luôn là Concert đã lưu; bên phải là bản nhạc cụ độc lập. Chỉnh sửa ở bên phải rồi dùng Save As/Save hoặc Export instrument MusicXML để giữ file nhạc cụ riêng.

Sau khi đóng ứng dụng hoặc dừng máy chủ: khởi động lại, Open MusicXML và chọn file Concert hoặc nhạc cụ đã lưu. Khi mở file nhạc cụ, ứng dụng mở nó như một tài liệu MusicXML độc lập để tiếp tục chỉnh sửa đúng cao độ đã ghi. Ứng dụng không tự phục hồi nhãn lựa chọn Stage 2, sáu biến thể, Undo/Redo hoặc danh sách phiên cũ. Không tạo lại nhạc cụ từ file written score đã mở lại nếu muốn tránh chuyển giọng lần thứ hai; để tạo mới, mở Concert gốc đã lưu.

## Xuất file

MusicXML giữ dữ liệu ký âm để sửa tiếp. Export PDF tạo bản in từ Working Score hiện tại, cả Concert và nhạc cụ; kiểm tra file PDF đã tải xuống. PDF không dùng để phục hồi phiên soạn nhạc. Thay đổi chưa lưu, bản Demo và các biến thể nhạc cụ chỉ còn trong bộ nhớ sẽ mất khi đóng/khởi động lại; Save từng bản cần giữ. Phiên backend cũng có thời hạn.

## Giới hạn

Chỉ chạy local, một tiến trình, không phải triển khai production hoặc chia sẻ qua mạng. Chưa bao gồm nhập PDF/hình ảnh và OMR thật. Demo vẫn là mô phỏng. Không có AI Agent. Không tự sửa nốt hoặc sáng tác phần còn thiếu. Bản nhạc riêng tư không được đóng gói. Bản gốc không đổi trừ khi chính người dùng chọn ghi đè file đó trong hộp thoại lưu.

Giữ manifest.json, requirements.lock và các giấy phép trong runtime/ và web/fonts/. Muốn dùng trên hệ điều hành/Python khác cần đóng gói và kiểm chứng lại trên máy đích.
