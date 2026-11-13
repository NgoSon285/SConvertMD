"""Chuyển file (PDF, Office, ảnh...) sang Markdown, có OCR cho bản scan.
OCR cần Tesseract: brew install tesseract tesseract-lang
"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

EXTS = {".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".csv", ".html", ".htm",
        ".json", ".xml", ".txt", ".epub", ".msg"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
OCR_LANG = "vie+eng"
MIN_CHARS_PER_PAGE = 30  # ít hơn mức này -> coi là PDF scan
PROMPT_FILE = Path(__file__).with_name("PROMPT.md")


# ---------- OCR ----------

# App mở từ Finder/Explorer không có PATH của terminal -> dò các nơi cài phổ biến
TESSERACT_PATHS = ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract",
                   r"C:\Program Files\Tesseract-OCR\tesseract.exe"]
BREW_PATHS = ["/opt/homebrew/bin/brew", "/usr/local/bin/brew"]
# Dữ liệu ngôn ngữ tự tải về đây -> giống nhau trên mọi máy, không cần quyền admin
TESSDATA_DIR = Path.home() / ".sconvertmd" / "tessdata"
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{}.traineddata"


def _first_existing(paths):
    return next((p for p in paths if Path(p).exists()), None)


def find_tesseract():
    return shutil.which("tesseract") or _first_existing(TESSERACT_PATHS)


def install_tesseract(log):
    if sys.platform == "darwin":
        brew = shutil.which("brew") or _first_existing(BREW_PATHS)
        if not brew:
            raise RuntimeError("Cần cài Homebrew trước (https://brew.sh), rồi mở lại app")
        cmd = [brew, "install", "tesseract"]
    elif sys.platform == "win32":
        cmd = ["winget", "install", "-e", "--id", "UB-Mannheim.TesseractOCR",
               "--accept-source-agreements", "--accept-package-agreements"]
    else:
        raise RuntimeError("Hãy cài bằng lệnh: sudo apt install tesseract-ocr")
    log("⏳ Đang cài Tesseract… (vài phút, Windows có thể hỏi quyền admin)")
    r = subprocess.run(cmd, capture_output=True, text=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if not find_tesseract():
        raise RuntimeError(f"Cài Tesseract thất bại:\n{(r.stdout + r.stderr)[-800:]}")
    log("✓  Đã cài Tesseract")


def ensure_lang_data(log):
    import requests
    TESSDATA_DIR.mkdir(parents=True, exist_ok=True)
    for lang in OCR_LANG.split("+"):
        f = TESSDATA_DIR / f"{lang}.traineddata"
        if f.exists():
            continue
        log(f"⏳ Đang tải dữ liệu OCR '{lang}' (chỉ lần đầu)…")
        r = requests.get(TESSDATA_URL.format(lang), timeout=120)
        r.raise_for_status()
        tmp = f.with_suffix(".part")  # tải xong mới đổi tên -> không để lại file hỏng
        tmp.write_bytes(r.content)
        tmp.rename(f)


def ocr_image(img) -> str:
    import pytesseract
    cmd = find_tesseract()
    if not cmd:
        raise RuntimeError("Chưa cài Tesseract nên không OCR được")
    pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract.image_to_string(img, lang=OCR_LANG,
                                       config=f'--tessdata-dir "{TESSDATA_DIR}"')


def ocr_pdf(path: Path) -> str:
    import fitz  # pymupdf
    from PIL import Image
    parts = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, 1):
            png = page.get_pixmap(dpi=300).tobytes("png")
            parts.append(f"## Trang {i}\n\n{ocr_image(Image.open(io.BytesIO(png)))}")
    return "\n\n".join(parts)


def pdf_is_scanned(path: Path, text: str) -> bool:
    # ponytail: xét cả file; PDF trộn trang chữ + trang scan sẽ bỏ sót trang scan -> OCR từng trang nếu cần
    import fitz
    with fitz.open(path) as doc:
        return len(text.strip()) < MIN_CHARS_PER_PAGE * max(doc.page_count, 1)


# ---------- Chuyển đổi ----------

def to_markdown(md, f: Path, ocr: bool) -> str:
    ext = f.suffix.lower()
    if ext in IMAGE_EXTS:
        from PIL import Image
        with Image.open(f) as img:
            return ocr_image(img)
    text = md.convert(str(f)).text_content
    if ocr and ext == ".pdf" and pdf_is_scanned(f, text):
        return ocr_pdf(f)
    return text


def convert_folder(src: Path, dst: Path, log, progress=lambda i, n: None, ocr=True):
    from markitdown import MarkItDown  # import chậm, để trong thread
    md = MarkItDown()
    if ocr:
        try:
            ensure_lang_data(log)
        except Exception as e:
            log(f"✗  Không tải được dữ liệu OCR (kiểm tra mạng): {e}")
    exts = EXTS | IMAGE_EXTS if ocr else EXTS
    files = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in exts]
    progress(0, len(files))
    ok = 0
    for i, f in enumerate(files, 1):
        rel = f.relative_to(src)
        # giữ đuôi gốc trong tên để a.pdf và a.docx không đè nhau
        out = dst / rel.parent / (rel.name + ".md")
        try:
            text = to_markdown(md, f, ocr)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(f"<!-- source: {rel} -->\n\n{text}", encoding="utf-8")
            ok += 1
            log(f"✓  {rel}")
        except Exception as e:
            log(f"✗  {rel}  —  {e}")
        progress(i, len(files))

    if PROMPT_FILE.exists():
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROMPT_FILE, dst / "PROMPT.md")
        log("📝 Đã thêm PROMPT.md (prompt mẫu)")
    log(f"\nHoàn tất: {ok}/{len(files)} file → {dst}")
