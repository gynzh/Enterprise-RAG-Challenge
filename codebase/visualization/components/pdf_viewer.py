"""PDF preview helpers for the RAG visualization dashboard.

The previous implementation tried to use the third-party ``gradio_pdf`` custom
component.  In recent Gradio 6.x environments that component can keep the page
in a perpetual front-end loading state.  This helper intentionally uses only
plain HTML and a small FastAPI route defined in ``visualization/app.py``.
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
        """Return an existing absolute PDF path, otherwise ``None``."""
        pdf_file = Path(pdf_path).expanduser().resolve()
        if pdf_file.exists() and pdf_file.is_file() and pdf_file.suffix.lower() == ".pdf":
            return pdf_file
        return None

    @staticmethod
    def get_pdf_path(pdf_path: str | Path) -> Optional[str]:
        """Return the resolved PDF path as a string, or ``None`` if missing."""
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        return str(pdf_file) if pdf_file else None

    @staticmethod
    def create_pdf_viewer(pdf_path: str | Path, doc_id: str) -> gr.HTML:
        """Create an iframe-based PDF preview.

        The iframe points to the local FastAPI route ``/pdf/{doc_id}``.  That
        route returns the file with ``Content-Disposition: inline`` so the
        browser's native PDF viewer can render it directly.  This avoids both
        base64 data-URI limits and third-party Gradio custom component issues.
        """
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        safe_doc_id = html.escape(str(doc_id))

        if not pdf_file:
            safe_path = html.escape(str(Path(pdf_path)))
            return gr.HTML(
                f"""
                <div class="error-card">
                  <h3>❌ PDF 文件加载失败</h3>
                  <p><strong>文件路径：</strong><code>{safe_path}</code></p>
                  <p><strong>文档 ID：</strong><code>{safe_doc_id}</code></p>
                  <p>请检查文件是否存在、路径是否正确，或是否有读取权限。</p>
                </div>
                """
            )

        file_size_mb = round(pdf_file.stat().st_size / (1024 * 1024), 2)
        cache_buster = int(pdf_file.stat().st_mtime)
        # doc_id is expected to be a sha-like id, but quote it to be safe.
        pdf_url = f"/pdf/{quote(str(doc_id), safe='')}?v={cache_buster}"
        safe_file_name = html.escape(pdf_file.name)
        safe_size = html.escape(str(file_size_mb))

        html_content = f"""
        <div class="pdf-viewer-container">
          <div class="pdf-viewer-header">
            <div>
              <h3>📄 PDF 文档预览</h3>
              <div class="pdf-meta">
                文档 ID：<code>{safe_doc_id}</code>
                <span class="pdf-meta-sep">|</span>
                文件：<code>{safe_file_name}</code>
                <span class="pdf-meta-sep">|</span>
                大小：{safe_size} MB
              </div>
            </div>
            <a class="pdf-download-link" href="{pdf_url}" target="_blank" rel="noopener">打开/下载 PDF</a>
          </div>
          <iframe
            class="pdf-preview-frame"
            src="{pdf_url}#toolbar=1&navpanes=0&view=FitH"
            title="PDF preview for {safe_doc_id}"
          ></iframe>
          <p class="pdf-fallback">
            如果预览区域为空白，通常是浏览器内置 PDF 查看器被禁用。请点击右上角“打开/下载 PDF”。
          </p>
        </div>
        """
        return gr.HTML(html_content)

    @staticmethod
    def create_simple_pdf_display(pdf_path: str | Path) -> gr.File:
        """Create a simple file component as a last-resort fallback."""
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        if pdf_file:
            return gr.File(value=str(pdf_file), label=f"PDF文档: {pdf_file.name}")
        return gr.File(label="PDF文件不存在")

    @staticmethod
    def get_pdf_info(pdf_path: str | Path) -> dict:
        """Get PDF file metadata."""
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
