# Task 04 — PDF → chỉnh sửa → MusicXML

Phạm vi Task 04 đã được Product Owner nghiệm thu ngày 2026-10-27. Bản Tenor v0.3 trước Task 04 được giữ nguyên.

## Khởi động

Trong Ubuntu WSL, chạy `python3 -B /đường-dẫn-gói/start.py --port 5185`, mở http://localhost:5185. Gói cần Python ABI đã ghi trong manifest, Audiveris hiện có tại /opt/audiveris/bin/Audiveris và mô hình vie/eng ở ~/.config/AudiverisLtd/audiveris/tessdata. Có thể đặt AUDIVERIS_EXECUTABLE và AUDIVERIS_TESSDATA_PATH để chỉ định vị trí khác. Không tự cài đặt hoặc tải mô hình. Gói không chứa Java/Audiveris/mô hình OCR.

## Nhập và sửa

Chọn profile Vocal song hoặc Choir/SATB cho nguồn nhiều bè/khuông, rồi nhập PDF/PNG/JPEG. Nhận dạng chạy một lần; thất bại phải báo lỗi và không thay bằng bản demo. PDF gốc ở bên trái chỉ đọc, được vẽ bằng PDF.js cục bộ để Fit/zoom và cuộn dọc độc lập; bản nhạc bên phải là bản nháp cần chỉnh sửa.

Chọn nốt để đổi cao độ, dấu hóa, voice và staff. Notes/Rest có trường độ từ nốt tròn đến móc tư (64th). Dot và Double dot là thao tác riêng. Grace before và Slashed grace tạo nốt luyến nhỏ trước nốt chọn, khác với Small chỉ đổi kích cỡ hiển thị. Groups có nhóm 3:2 hỗn hợp và các tỷ lệ đều 3:2, 2:3, 5:4, 6:4, 7:4, 9:8; mỗi cao độ tiếp tục chỉnh riêng được. Nhóm không tự đoán thành viên hoặc chèn đè nốt khác.

Mở mục sửa Measure để chọn chính xác ô nhịp và sửa meter, hóa biểu (không đổi cao độ), clef, số khuông, ô lấy đà hoặc vạch nhịp. Thay đổi thuộc tính đầu ô, không tự sửa các thay đổi giữa ô. Add measure nối thêm ô trống khi cấu trúc hiện tại được hỗ trợ.

Bấm lời để sửa Unicode hoặc chọn nốt rồi Edit lyrics/Add Verse để thêm lời thiếu. Công cụ Move lyric chuyển lời sang nốt và verse được chọn rõ ràng. Lời nhiều đoạn được sửa từng segment, không tự gộp hoặc đoán đổi font cũ. Voice thuộc về nốt; verse là dòng lời, hai khái niệm khác nhau.

## Lưu và dùng tiếp

Đối chiếu bản nhạc với từng trang nguồn, xác nhận ô “I compared this revision…” rồi Save/Save As thành MusicXML. Mỗi lần sửa nội dung phải xác nhận lại. Nếu trình duyệt tải file, giữ file rồi xác nhận đã nhận. Mở lại file để tiếp tục; phiên Undo/Redo không tồn tại sau khi đóng ứng dụng.

Bản Concert đã lưu là đầu vào đổi giọng/Instrument Scores; không chạy lại OMR khi transpose. Bản nhạc cụ bên phải độc lập; bản Concert gốc không đổi. PDF xuất là bản trình bày, MusicXML mới là dữ liệu chỉnh sửa tiếp.

## Giới hạn cần biết

OMR không bảo đảm nhận đúng nốt/bè/lời. PDF mã hóa không được hỗ trợ; bản quét chất lượng kém có thể thất bại. Giới hạn hiện hữu: 20 MB, tối đa 10 trang, timeout nhận dạng 120 giây. Không nhận dạng tự động lại. Không có AI Agent.

Không cam kết sao chép toàn bộ MuseScore/Symphony Pro, tuplet lồng nhau hoặc mọi dạng ký âm. Stage 2 giữ giới hạn bản đầu vào một part; không tự gộp dàn hợp xướng thành một nhạc cụ. Hạn chế còn lại và kết quả kiểm thử thực tế được ghi trong báo cáo Task 04.


## Bản sửa phản hồi — v0.2

- Hóa biểu đổi giữa bài không được áp ngược lên đầu bài. Khi XML thiếu hóa biểu đầu, khung hiển thị dùng trạng thái không dấu trước thay đổi đầu tiên, không suy giọng từ Am/C và không sửa pitch/alter/accidental của nốt. Muốn sửa dữ liệu hóa biểu, chọn đúng ô trong Measure correction.
- Cột EDIT có Dot/Double dot cho nốt đơn hoặc toàn bộ hợp âm. Với trường hợp OMR bỏ chấm của nốt đen như ô E7 đã đối chiếu, chọn nốt/hợp âm đầu rồi bấm “Missing dot +½”. Thao tác rõ ràng này đổi thành 1½ phách và đưa nhóm móc đơn sau sang mốc1½ trong cùng ô; cao độ và dấu hóa giữ nguyên. Dot thường giữ các mốc thời gian hiện có, còn sửa nhịp thiếu cần dùng đúng hành động trên.
- Rest mở bảng dấu lặng từ tròn đến64th. Chọn khoảng trống có voice/staff rõ ràng rồi chọn loại lặng; lặng móc đơn là½ phách nếu lấy nốt đen làm một phách.
- Ở chế độ Select, bấm text OCR hoặc pedal để chọn, rồi Delete; Undo khôi phục. Chế độ Text dùng để sửa chữ. Mục “Select OCR text or pedal mark to delete” cung cấp lựa chọn theo định danh nếu chữ trùng nhau hoặc chưa chọn được trên khuông.
- “Repair text recognized as lyrics”: chọn text OMR đã phân loại sai, sửa Unicode, chọn verse, Prepare syllable mapping, rồi chọn nốt đích cho từng âm tiết. Không có nốt nào được gán tự động. Có thể chọn xóa text gốc sau khi đã xác nhận ánh xạ; toàn bộ chuyển đổi là một bước Undo.
- “Chord symbols”: chọn nốt làm mốc, chọn root/dấu hóa/quality/suffix rồi Add. Suffix có thể là7,m,m(b5). Chọn chord có sẵn để Update, Move đến nốt đã chọn hoặc Delete. Không có hợp âm nào được tự suy từ giai điệu.
- Cảnh báo OMR được gom theo loại, có danh sách ô nhịp khi engine cung cấp vị trí. Mở phần cảnh báo để xem, không cần đọc các dòng trùng lặp trước khi chỉnh sửa.

Bản5184 cũ không bị thay thế. Lưu MusicXML đang sửa trước khi chuyển sang bản5185. Đây vẫn là ứng viên Task04, chưa được Product Owner nghiệm thu.


## Bổ sung thao tác soạn nhạc và thông báo Validate

- Trong Working Score, chọn **Select area**, kéo một hình chữ nhật bao quanh các đầu nốt. Các nốt được tô chọn. **Delete** xóa cả vùng chọn và giữ vị trí thời gian của nốt ngoài vùng; một lần **Undo** khôi phục cả nhóm.
- Sau khi khoanh vùng, chọn **Groups** để dùng các dạng tuplet/beam hiện có. Cao độ từng nốt vẫn sửa độc lập bằng kéo chuột hoặc công cụ cao độ/dấu hóa.
- Chọn **Notes** hoặc **Rest**, bấm vị trí trên khuôn nhạc, chọn voice và trường độ để thêm nội dung. Có thể dùng mục “Insert missing content at an explicit position” để chỉ rõ ô, phách, voice, staff khi bản OMR đặt vị trí chưa đúng. Các giá trị nhịp chưa hoàn chỉnh trong lúc sửa không bị tự động lấp bằng nốt hoặc dấu lặng.
- Mở **Select OCR text or score mark to delete** để chọn/xóa text, pedal, dynamics như p/ff, wedge hoặc ký hiệu OMR nhận thừa. Undo khôi phục ký hiệu. Không tự thêm ký hiệu dựa theo suy đoán.
- Bấm **Validate** để xem cảnh báo nhịp và cảnh báo nhận diện trong phần thông báo. Các cảnh báo không tự sửa hay đổi bản nhạc.
- Hóa biểu, nhịp và vạch nhịp do OMR đọc vẫn cần đối chiếu với PDF gốc; bản thử nghiệm không bảo đảm nhận diện đúng mọi bản in. Người dùng có công cụ sửa trực tiếp và lưu MusicXML đã sửa.


## Giao diện trực tiếp và MusicXML nguyên trạng (v0.9)

Bản nhạc là nơi thao tác chính. Bấm đầu nốt để mở công cụ tại chỗ; kéo để đổi cao độ. Giữ Shift và kéo khoanh vùng (hoặc Select area), rồi Delete để xóa nhóm. Bấm ký hiệu cường độ/Ped. hoặc chữ để hiện thao tác xóa/sửa ngay cạnh đối tượng. Text mở ô nhập ngay trên bản nhạc. Dots là một nhóm trong Edit.

Chọn Chords rồi bấm vị trí trên khuôn hoặc đầu nốt cần đặt hợp âm. Nhập root/quality/suffix theo hòa âm của mình. Bấm hợp âm có sẵn để sửa. Không có việc hệ thống tự chọn hòa âm. Bảng công cụ là lớp nổi, không đẩy bản nhạc xuống dưới; đóng bằng ×. More chỉ giữ các công cụ phụ/khôi phục dữ liệu OMR khó, không phải đường thao tác thường ngày. Các công cụ hỗ trợ đều dùng chung ở Concert và Instrument Score.

Edit Only chỉ ẩn Original Source và mở rộng Working Score; giữ nguyên công cụ, vùng chọn và chỉnh sửa. Compare hiện lại bản gốc, không tải lại tài liệu.

Nếu nhập MusicXML và giữ nguyên (không đổi Concert Key, không chỉnh sửa), có thể chọn Instrument Scores ngay. Nhãn “Imported MusicXML · unchanged” chỉ rõ đang dùng file nhập, không tuyên bố đã Save mới. Sau khi có thay đổi, cần Save trước khi chuyển bản thay đổi sang nhạc cụ. PDF/ảnh OMR vẫn cần đối chiếu và Save bản đã sửa trước khi chuyển nhạc cụ.


## Về Home mà không lưu

Khi có thay đổi chưa lưu, Home mở ba lựa chọn: mở từng bản để Save, Continue editing, hoặc Discard changes and go Home. Chọn Discard chủ động bỏ tất cả thay đổi chưa lưu của Concert và các bản nhạc cụ đang mở rồi về trang nhập file. Các file đã lưu vẫn giữ nguyên; thao tác này không tự Save hay tải file. Escape/Continue editing giữ nguyên công việc. Khi đang lưu hoặc đang áp dụng chỉnh sửa, chờ thao tác hoàn tất trước khi rời trang.


### Giọng gốc khi lưu bản thiếu hóa biểu đầu bài

Nếu Save yêu cầu chọn giọng gốc, chọn Trưởng/Thứ và tên giọng rồi bấm Xác nhận và lưu MusicXML. Có thể bấm Dùng gợi ý nếu phù hợp; gợi ý dựa trên hợp âm đầu được nhận diện, không phải kết luận chắc chắn. Anh luôn có thể chọn giọng khác theo bản gốc. Khai báo này không chuyển cao độ các nốt. Sau khi lưu, bản nhạc cụ sử dụng hóa biểu nguồn đã khai báo. Muốn chuyển cao độ toàn bản Concert, dùng Concert Key riêng.


### Quãng viết mặc định dễ đọc cho Sax

Alto E♭ mặc định viết xuống3bán âm (1cung rưỡi); Soprano B♭ viết lên2bán âm (1cung); Tenor B♭ cũng viết lên2bán âm như Soprano. Khi đổi nhạc cụ, ứng dụng chọn mặc định riêng của nhạc cụ đó. Nếu anh tự đổi Up/Down, ứng dụng nhớ lựa chọn đó riêng cho từng nhạc cụ trong phiên hiện tại. Bản Concert không bị đổi. Quãng âm thực tế khi chơi Tenor hoặc Alto theo lựa chọn thấp có thể thấp hơn Concert một quãng tám; đây là lựa chọn quãng viết dễ đọc đã được anh phê duyệt.


## Các thao tác đã hoàn thiện

- Compare và Edit Only có cùng công cụ; Edit Only chỉ ẩn bản gốc. Chỉnh nốt, lời, hợp âm và các đối tượng được hỗ trợ trực tiếp trên Working Score.
- Add Chord: chọn công cụ, bấm vị trí trên bản nhạc, nhập ký hiệu như Bm/G/E7; bấm hợp âm hiện có để sửa hoặc xóa.
- Bản MusicXML nhập có giọng đầu bài rõ ràng và chưa thay đổi có thể dùng Instrument Scores ngay. Bản OMR cần đối chiếu và lưu sau chỉnh sửa.
- Nếu chưa có giọng gốc đầu bài, khi Save hãy xác nhận trưởng/thứ và giọng. Gợi ý chỉ áp dụng khi người dùng chọn; xác nhận này không chuyển cao độ.
- Concert Key: xác nhận giọng hiện tại, chọn giọng đích và Up/Down rồi Apply. Cùng giọng + Down hạ một quãng tám, giữ nguyên giọng; cùng giọng + Up giữ nguyên cao độ. Nút × hoặc Esc đóng khung mà không áp dụng.
- Các đoạn đổi giọng được chuyển cùng khoảng; nếu cách ghi làm một đoạn vượt quá 7 dấu hóa, hệ thống yêu cầu người dùng chọn cách ghi tương đương được hỗ trợ.
- Alto mặc định bản viết thấp hơn Concert 3 bán âm; Soprano và Tenor mặc định cao hơn 2 bán âm cho dễ đọc. Bản Tenor theo cách ghi đã được PO chọn giống Soprano, âm thực trên Tenor thấp hơn một quãng tám. Đây là lựa chọn âm vực bản viết, không đổi bản Concert.
- Export PDF dùng A4 đứng, lề 12 mm và khoảng cách khuôn/lời/nốt gọn hơn. Bài dài tự chia trang; không ép mọi bài vào một trang. MusicXML vẫn là dữ liệu chỉnh sửa tiếp.
- Home cho phép tiếp tục sửa, lưu, hoặc bỏ thay đổi chưa lưu để nhập bài khác. Các tệp đã lưu không bị xóa.
