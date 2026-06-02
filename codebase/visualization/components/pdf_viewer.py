"""PDF preview helpers for the RAG visualization dashboard.

This module intentionally uses only plain HTML plus the FastAPI /pdf/{doc_id}
route from visualization/app.py. It avoids third-party Gradio PDF components and
base64 data URIs.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import gradio as gr


class PDFViewer:
    """Utility methods for rendering a PDF report preview."""

    @staticmethod
    def resolve_pdf_path(pdf_path: str | Path) -> Optional[Path]:
        pdf_file = Path(pdf_path).expanduser().resolve()
        if pdf_file.exists() and pdf_file.is_file() and pdf_file.suffix.lower() == ".pdf":
            return pdf_file
        return None

    @staticmethod
    def get_pdf_path(pdf_path: str | Path) -> Optional[str]:
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        return str(pdf_file) if pdf_file else None

    @staticmethod
    def create_pdf_viewer(pdf_path: str | Path, doc_id: str) -> gr.HTML:
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        safe_doc_id = html.escape(str(doc_id))
        if not pdf_file:
            safe_path = html.escape(str(Path(pdf_path)))
            return gr.HTML(
                '<section class="error-card">'
                '<h3>PDF \u6587\u4ef6\u52a0\u8f7d\u5931\u8d25</h3>'
                f'<p><strong>\u6587\u4ef6\u8def\u5f84:</strong> <code>{safe_path}</code></p>'
                f'<p><strong>\u6587\u6863 ID:</strong> <code>{safe_doc_id}</code></p>'
                '<p>\u8bf7\u68c0\u67e5\u6587\u4ef6\u662f\u5426\u5b58\u5728\u3001\u8def\u5f84\u662f\u5426\u6b63\u786e\uff0c\u6216\u662f\u5426\u6709\u8bfb\u53d6\u6743\u9650\u3002</p>'
                '</section>'
            )

        file_size_mb = round(pdf_file.stat().st_size / (1024 * 1024), 2)
        cache_buster = int(pdf_file.stat().st_mtime)
        pdf_url = f"/pdf/{quote(str(doc_id), safe='')}?v={cache_buster}"
        safe_url = html.escape(pdf_url, quote=True)
        safe_file_name = html.escape(pdf_file.name)
        safe_size = html.escape(str(file_size_mb))

        html_content = f'''
        <section class="pdf-viewer-container">
            <div class="pdf-viewer-header">
                <div>
                    <h3>PDF \u6587\u6863\u9884\u89c8</h3>
                    <div class="pdf-meta">
                        <strong>\u6587\u6863 ID:</strong> <code>{safe_doc_id}</code><br>
                        <strong>\u6587\u4ef6:</strong> <code>{safe_file_name}</code>
                        <span class="pdf-meta-sep">|</span>
                        <strong>\u5927\u5c0f:</strong> {safe_size} MB
                    </div>
                </div>
                <a class="pdf-download-link" href="{safe_url}" target="_blank" rel="noopener noreferrer">\u6253\u5f00/\u4e0b\u8f7d PDF</a>
            </div>
            <iframe
                class="pdf-preview-frame"
                src="{safe_url}"
                title="PDF preview: {safe_file_name}"
            ></iframe>
            <p class="pdf-fallback">
                \u5982\u679c\u9884\u89c8\u533a\u57df\u4e3a\u7a7a\u767d\uff0c\u901a\u5e38\u662f\u6d4f\u89c8\u5668\u5185\u7f6e PDF \u67e5\u770b\u5668\u88ab\u7981\u7528\u3002\u8bf7\u70b9\u51fb\u53f3\u4e0a\u89d2\u201c\u6253\u5f00/\u4e0b\u8f7d PDF\u201d\u3002
            </p>
        </section>
        '''
        return gr.HTML(html_content)

    @staticmethod
    def create_simple_pdf_display(pdf_path: str | Path) -> gr.File:
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        if pdf_file:
            return gr.File(value=str(pdf_file), label=f"PDF: {pdf_file.name}")
        return gr.File(label="PDF file not found")

    @staticmethod
    def get_pdf_info(pdf_path: str | Path) -> dict:
        pdf_file = Path(pdf_path).expanduser().resolve()
        info = {
            "exists": pdf_file.exists(),
            "file_name": pdf_file.name,
            "file_path": str(pdf_file),
            "size_bytes": 0,
            "size_mb": 0,
        }
        if pdf_file.exists() and pdf_file.is_file():
            size_bytes = pdf_file.stat().st_size
            info.update(
                {
                    "size_bytes": size_bytes,
                    "size_mb": round(size_bytes / (1024 * 1024), 2),
                }
            )
        return info
