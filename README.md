# SConvertMD

Chuyển cả thư mục PDF, Excel, Word, PowerPoint, ảnh… thành file Markdown cho LLM. Có OCR tiếng Việt cho PDF scan và ảnh.

## Chạy từ mã nguồn

```bash
uv run --python 3.12 app.py
```

## Đóng gói thành app

Phải build trên đúng hệ điều hành đích: build trên Mac ra `.app`, build trên Windows ra `.exe`.

**Bước 1: cài uv** (một lần)
- macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows (PowerShell): `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

**Bước 2: build** (lệnh giống nhau trên cả hai hệ điều hành, chạy trong thư mục dự án)

```bash
uv run --python 3.12 --with "markitdown[all]" --with pymupdf --with pytesseract --with pillow --with customtkinter --with pyinstaller pyinstaller --noconfirm --windowed --name SConvertMD --add-data "PROMPT.md:." --collect-all customtkinter --collect-all magika --collect-all markitdown app.py
```

**Kết quả** nằm trong `dist/`:
- macOS: `dist/SConvertMD.app`. Kéo vào thư mục Applications là dùng được.
- Windows: thư mục `dist\SConvertMD\`. Chạy `SConvertMD.exe` và gửi cho người khác **cả thư mục** (nén zip lại).

## OCR trên máy người dùng

Lần đầu bật OCR, nếu máy chưa có Tesseract, app sẽ hỏi rồi tự cài:
- macOS: cài qua Homebrew (máy cần có sẵn Homebrew: https://brew.sh)
- Windows: cài qua `winget` (có sẵn trên Windows 10/11, sẽ hỏi quyền admin)

Dữ liệu tiếng Việt và tiếng Anh (~28MB) được tải một lần vào `~/.sconvertmd/tessdata`.

## Lưu ý khi gửi app cho người khác

- **macOS:** app chưa được ký nên lần đầu sẽ bị chặn. Bấm chuột phải vào app → Open → Open. Nếu vẫn báo hỏng: `xattr -cr /Applications/SConvertMD.app`
- **Windows:** SmartScreen có thể cảnh báo. Bấm "More info" → "Run anyway".
