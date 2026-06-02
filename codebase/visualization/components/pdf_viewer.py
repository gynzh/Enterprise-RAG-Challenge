import base64
import html
from pathlib import Path
from typing import Optional

import gradio as gr


class PDFViewer:
    """PDF文档在线查看器。"""

    @staticmethod
    def load_pdf_base64(pdf_path: str) -> Optional[str]:
        """将 PDF 文件转换为 base64 编码。"""
        pdf_file = Path(pdf_path)
        if not pdf_file.exists() or not pdf_file.is_file():
            return None

        try:
            with pdf_file.open("rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        except Exception as exc:
            print(f"加载PDF文件失败: {exc}")
            return None

    @staticmethod
    def create_pdf_viewer(pdf_path: str, doc_id: str) -> gr.HTML:
        """创建可直接在线预览的 PDF HTML。"""
        pdf_file = Path(pdf_path)
        safe_doc_id = html.escape(str(doc_id))
        safe_pdf_path = html.escape(str(pdf_file))

        pdf_base64 = PDFViewer.load_pdf_base64(str(pdf_file))
        if not pdf_base64:
            return gr.HTML(
                f"""
                <div class="pdf-error-card">
                    <h3>❌ PDF文件加载失败</h3>
                    <p><strong>文件路径:</strong> <code>{safe_pdf_path}</code></p>
                    <p><strong>文档ID:</strong> <code>{safe_doc_id}</code></p>
                    <p>请检查文件是否存在、路径是否正确，或是否有读取权限。</p>
                </div>
                """
            )

        file_size_mb = round(pdf_file.stat().st_size / (1024 * 1024), 2)
        data_uri = f"data:application/pdf;base64,{pdf_base64}"

        html_content = f"""
        <div class="pdf-viewer-container">
            <div class="pdf-viewer-header">
                <div>
                    <h3>📄 PDF文档预览</h3>
                    <div class="pdf-meta">
                        文档ID: <code>{safe_doc_id}</code>
                        <span class="pdf-meta-sep">|</span>
                        文件大小: {file_size_mb} MB
                    </div>
                </div>
                <a class="pdf-download-link" href="{data_uri}" download="{html.escape(pdf_file.name)}">下载PDF</a>
            </div>

            <iframe
                class="pdf-preview-frame"
                src="{data_uri}"
                title="PDF preview - {safe_doc_id}"
            ></iframe>

            <div class="pdf-fallback">
                如果预览区域为空白，请确认浏览器允许内置 PDF 查看器；也可以点击上方“下载PDF”后本地查看。
            </div>
        </div>
        """
        return gr.HTML(html_content)

    @staticmethod
    def create_simple_pdf_display(pdf_path: str) -> gr.File:
        """创建简单的 PDF 文件下载组件（备用方案）。"""
        pdf_file = Path(pdf_path)
        if pdf_file.exists():
            return gr.File(value=str(pdf_file), label=f"PDF文档: {pdf_file.name}")
        return gr.File(label="PDF文件不存在")

    @staticmethod
    def get_pdf_info(pdf_path: str) -> dict:
        """获取 PDF 文件信息。"""
        pdf_file = Path(pdf_path)
        info = {
            "exists": pdf_file.exists(),
            "file_name": pdf_file.name,
            "file_path": str(pdf_file),
            "size_bytes": 0,
            "size_mb": 0,
        }
        if pdf_file.exists():
            size_bytes = pdf_file.stat().st_size
            info.update(
                {
                    "size_bytes": size_bytes,
                    "size_mb": round(size_bytes / (1024 * 1024), 2),
                }
            )
        return info
