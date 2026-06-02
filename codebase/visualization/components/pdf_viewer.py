"""Utilities for displaying PDF reports in the Gradio visualization app.

This module intentionally does not embed the whole PDF as a base64 string in
``gr.HTML``. Large data URIs are fragile in Gradio/browser combinations and can
make the left preview pane appear blank. The app uses ``gradio_pdf`` when it is
installed and falls back to a Gradio-served local file URL for HTML preview.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import gradio as gr


class PDFViewer:
    """PDF document preview helpers."""

    @staticmethod
    def resolve_pdf_path(pdf_path: str | Path) -> Optional[Path]:
        """Return an existing absolute PDF path, otherwise ``None``."""
        pdf_file = Path(pdf_path).expanduser().resolve()
        if pdf_file.exists() and pdf_file.is_file() and pdf_file.suffix.lower() == ".pdf":
            return pdf_file
        return None

    @staticmethod
    def get_pdf_path(pdf_path: str | Path) -> Optional[str]:
        """Return a string path suitable for Gradio file/PDF outputs."""
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        return str(pdf_file) if pdf_file else None

    @staticmethod
    def _gradio_file_url(pdf_file: Path, api_prefix: str = "/gradio_api/file=") -> str:
        """Build a Gradio file-serving URL for a local PDF.

        ``Blocks.launch(allowed_paths=[...])`` must include the PDF parent
        directory. ``/gradio_api/file=`` is used by newer Gradio versions; the
        generated HTML also includes a ``/file=`` fallback link for older ones.
        """
        # Convert Windows paths to slash form so the URL remains browser-friendly.
        path_for_url = pdf_file.as_posix()
        return f"{api_prefix}{quote(path_for_url, safe='/:')}"

    @staticmethod
    def create_pdf_viewer(pdf_path: str | Path, doc_id: str) -> gr.HTML:
        """Create an HTML fallback preview for environments without gradio_pdf."""
        pdf_file = PDFViewer.resolve_pdf_path(pdf_path)
        safe_doc_id = html.escape(str(doc_id))

        if not pdf_file:
            safe_path = html.escape(str(Path(pdf_path)))
            return gr.HTML(
                f"""
                <section class="error-card">
                  <h3>❌ PDF文件加载失败</h3>
                  <p><strong>文件路径：</strong><code>{safe_path}</code></p>
                  <p><strong>文档ID：</strong><code>{safe_doc_id}</code></p>
                  <p>请检查文件是否存在、路径是否正确，或是否有读取权限。</p>
                </section>
                """
            )

        file_size_mb = round(pdf_file.stat().st_size / (1024 * 1024), 2)
        file_url_new = PDFViewer._gradio_file_url(pdf_file, "/gradio_api/file=")
        file_url_old = PDFViewer._gradio_file_url(pdf_file, "/file=")
        safe_file_name = html.escape(pdf_file.name)
        safe_size = html.escape(str(file_size_mb))

        html_content = f"""
        <section class="pdf-viewer-container">
          <div class="pdf-viewer-header">
            <div>
              <h3>📄 PDF文档预览</h3>
              <div class="pdf-meta">
                <span>文档ID：<code>{safe_doc_id}</code></span>
                <span class="pdf-meta-sep">|</span>
                <span>文件：<code>{safe_file_name}</code></span>
                <span class="pdf-meta-sep">|</span>
                <span>大小：{safe_size} MB</span>
              </div>
            </div>
            <a class="pdf-download-link" href="{file_url_new}" target="_blank" rel="noopener">打开/下载PDF</a>
          </div>

          <iframe
            class="pdf-preview-frame"
            src="{file_url_new}#toolbar=1&navpanes=0&scrollbar=1"
            title="PDF preview for {safe_doc_id}">
          </iframe>

          <p class="pdf-fallback">
            如果预览仍为空白，请点击“打开/下载PDF”。旧版 Gradio 可尝试
            <a href="{file_url_old}" target="_blank" rel="noopener">备用打开链接</a>。
          </p>
        </section>
        """
        return gr.HTML(html_content)

    @staticmethod
    def create_simple_pdf_display(pdf_path: str | Path) -> gr.File:
        """Create a simple download component as a last-resort fallback."""
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
