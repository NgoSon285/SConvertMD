# /// script
# requires-python = ">=3.10"
# dependencies = ["markitdown[all]", "pymupdf", "pytesseract", "pillow", "customtkinter"]
# ///
"""Giao diện SConvertMD. Chạy: uv run --python 3.12 app.py"""
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from converter import convert_folder, find_tesseract, install_tesseract


def open_folder(path: Path):
    if sys.platform == "darwin":
        subprocess.run(["open", path])
    elif sys.platform == "win32":
        import os
        os.startfile(path)
    else:
        subprocess.run(["xdg-open", path])


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        self.title("SConvertMD")
        self.geometry("760x560")
        self.minsize(600, 440)
        self.q = queue.Queue()
        self.src, self.dst = ctk.StringVar(), ctk.StringVar()
        self.ocr = ctk.BooleanVar(value=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._build_header()
        self._build_folder_card()
        self._build_action_bar()
        self._build_log()
        self.after(100, self.drain)

    # ---------- Dựng giao diện ----------

    def _build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        ctk.CTkLabel(head, text="SConvertMD", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(head, text="Chuyển PDF, Excel, Word, PowerPoint, ảnh… thành Markdown cho LLM",
                     text_color="gray").pack(anchor="w")

    def _build_folder_card(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        card.columnconfigure(1, weight=1)
        for row, (label, var, hint) in enumerate([
            ("Thư mục nguồn", self.src, "Chọn thư mục chứa tài liệu…"),
            ("Thư mục đích", self.dst, "Nơi lưu file .md…"),
        ]):
            pady = (14 if row == 0 else 6, 6)
            ctk.CTkLabel(card, text=label, width=110, anchor="w").grid(
                row=row, column=0, padx=(16, 8), pady=pady, sticky="w")
            ctk.CTkEntry(card, textvariable=var, placeholder_text=hint).grid(
                row=row, column=1, sticky="ew", pady=pady)
            ctk.CTkButton(card, text="Chọn", width=72, command=lambda v=var: self.pick(v)).grid(
                row=row, column=2, padx=16, pady=pady)
        ctk.CTkSwitch(card, text="OCR cho PDF scan và ảnh (tiếng Việt + Anh, chậm hơn)",
                      variable=self.ocr).grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=(6, 14))

    def _build_action_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=24, pady=8)
        bar.columnconfigure(1, weight=1)
        self.btn = ctk.CTkButton(bar, text="Chuyển đổi", height=38, width=140,
                                 font=ctk.CTkFont(size=14, weight="bold"), command=self.start)
        self.btn.grid(row=0, column=0, rowspan=2)
        self.bar = ctk.CTkProgressBar(bar)
        self.bar.set(0)
        self.bar.grid(row=0, column=1, sticky="ew", padx=16, pady=(4, 0))
        self.status = ctk.CTkLabel(bar, text="Sẵn sàng", text_color="gray", anchor="w")
        self.status.grid(row=1, column=1, sticky="w", padx=16)
        self.open_btn = ctk.CTkButton(bar, text="Mở kết quả", width=110, height=38, state="disabled",
                                      fg_color="transparent", border_width=1,
                                      text_color=("gray10", "gray90"),
                                      command=lambda: open_folder(Path(self.dst.get())))
        self.open_btn.grid(row=0, column=2, rowspan=2)

    def _build_log(self):
        self.log_box = ctk.CTkTextbox(self, corner_radius=12, font=ctk.CTkFont(family="Menlo", size=12))
        self.log_box.grid(row=3, column=0, sticky="nsew", padx=24, pady=(8, 24))
        self.log_box.configure(state="disabled")

    # ---------- Xử lý sự kiện ----------

    def pick(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(d)
            if var is self.src and not self.dst.get():
                self.dst.set(d + "_md")

    # thread chỉ đẩy vào queue; UI chỉ cập nhật trên main thread
    def log(self, msg):
        self.q.put(("log", msg))

    def progress(self, i, n):
        self.q.put(("progress", (i, n)))

    def drain(self):
        while not self.q.empty():
            kind, val = self.q.get()
            if kind == "log":
                self.log_box.configure(state="normal")
                self.log_box.insert("end", val + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
            elif kind == "progress":
                i, n = val
                self.bar.set(i / n if n else 1)
                self.status.configure(text=f"{i}/{n} file" if n else "Không có file nào phù hợp")
            elif kind == "done":
                self.btn.configure(state="normal", text="Chuyển đổi")
                self.open_btn.configure(state="normal")
        self.after(100, self.drain)

    def start(self):
        src, dst = Path(self.src.get()), Path(self.dst.get())
        if not self.src.get() or not src.is_dir() or not self.dst.get():
            self.status.configure(text="⚠ Hãy chọn thư mục nguồn và đích hợp lệ")
            return
        self.btn.configure(state="disabled", text="Đang chạy…")
        self.open_btn.configure(state="disabled")
        self.bar.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.status.configure(text="Đang quét file…")
        ocr = self.ocr.get()
        need_install = False
        if ocr and not find_tesseract():
            need_install = messagebox.askyesno(
                "Chưa có Tesseract",
                "OCR (đọc chữ từ PDF scan và ảnh) cần phần mềm Tesseract nhưng máy chưa cài.\n\n"
                "Cài tự động ngay bây giờ?\n(Chọn 'No' để chuyển đổi tiếp mà không OCR)")
            if not need_install:
                ocr = False
                self.log("ℹ  Bỏ qua OCR vì chưa cài Tesseract")

        def run():
            nonlocal ocr
            if need_install:
                try:
                    install_tesseract(self.log)
                except Exception as e:
                    self.log(f"✗  {e}\nℹ  Tiếp tục chuyển đổi không OCR")
                    ocr = False
            try:
                convert_folder(src, dst, self.log, self.progress, ocr)
            except Exception as e:
                self.log(f"Lỗi: {e}")
            self.q.put(("done", None))
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
