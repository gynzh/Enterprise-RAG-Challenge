"""RAG Challenge result visualization app.

v3 fixes:
1. Remove the third-party ``gradio_pdf`` custom component from the runtime path.
   In Gradio 6.x it can leave the browser stuck at "加载中...".
2. Do not rely on ``Blocks.load`` to populate the initial page.  All initial
   HTML is rendered before the UI is served, so the dashboard is visible even if
   front-end events fail.
3. Serve PDFs through a small FastAPI route ``/pdf/{doc_id}`` with
   ``Content-Disposition: inline`` and display them in a normal iframe.
4. Keep all tabs pre-rendered and refresh them together on document changes.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import gradio as gr
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import uvicorn

# Add visualization directory to Python path so ``components`` imports work when
# running either ``python app.py`` or ``python run.py`` from this directory.
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from components.data_loader import RAGResultsLoader  # noqa: E402
from components.pdf_viewer import PDFViewer  # noqa: E402


class RAGVisualizationApp:
    """RAG Challenge reproduction result visualization app."""

    def __init__(self, data_path: str | Path = "../data/test_set"):
        data_path_obj = Path(data_path)
        if not data_path_obj.is_absolute():
            data_path_obj = current_dir / data_path_obj

        self.data_path = data_path_obj.resolve()
        self.loader = RAGResultsLoader(str(self.data_path))
        self.available_docs = self.loader.get_available_documents()
        self.available_configs = self.loader.get_available_configs()
        self.current_doc = self.available_docs[0] if self.available_docs else ""
        self.current_config = self.available_configs[0] if self.available_configs else "gemini_thinking_fc"

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _json_preview(data: Any, limit: int = 8000) -> str:
        """Return an escaped JSON preview that is safe to embed in HTML."""
        preview = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        if len(preview) > limit:
            preview = preview[:limit] + "\n\n... 内容过长，已截断"
        return html.escape(preview)

    @staticmethod
    def _extract_pages(parsing_data: dict) -> list:
        """Extract pages from parsed data, compatible with list/dict content."""
        content = parsing_data.get("content", [])
        if isinstance(content, list):
            return content
        if isinstance(content, dict):
            return content.get("pages", [])
        return []

    @staticmethod
    def _count_text_length_from_pages(pages: list) -> int:
        """Count text characters in parsed page/block structures."""
        total_length = 0
        for page in pages:
            if isinstance(page, str):
                total_length += len(page)
                continue
            if not isinstance(page, dict):
                continue

            page_content = page.get("content", [])
            if isinstance(page_content, list):
                for block in page_content:
                    if isinstance(block, dict):
                        total_length += len(str(block.get("text", "")))
                    else:
                        total_length += len(str(block))
            elif isinstance(page_content, str):
                total_length += len(page_content)
            else:
                total_length += len(str(page.get("text", "")))
        return total_length

    @staticmethod
    def _card(title: str, body_html: str, css_class: str = "content-card") -> str:
        return f"""
        <div class="{css_class}">
          <h3>{html.escape(title)}</h3>
          {body_html}
        </div>
        """

    @staticmethod
    def _error(message: str) -> str:
        return f"""
        <div class="error-card">
          <h3>❌ 出错</h3>
          <p>{html.escape(message)}</p>
        </div>
        """

    @staticmethod
    def _stats_grid(items: Iterable[tuple[str, Any]]) -> str:
        cells = []
        for label, value in items:
            cells.append(
                f"""
                <div class="stat-item">
                  <div class="stat-label">{html.escape(str(label))}</div>
                  <div class="stat-value">{html.escape(str(value))}</div>
                </div>
                """
            )
        return f"<div class=\"stats-grid\">{''.join(cells)}</div>"

    def _current_pdf_path(self) -> Path:
        return self.data_path / "pdf_reports" / f"{self.current_doc}.pdf"

    def _pdf_output(self) -> str:
        return PDFViewer.create_pdf_viewer(self._current_pdf_path(), self.current_doc).value

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def update_document(self, doc_id: str):
        """Update selected document and refresh all content panes."""
        self.current_doc = doc_id or ""
        return self.refresh_all_content()

    def update_config(self, config: str):
        """Update selected QA config and refresh QA content."""
        self.current_config = config or ""
        return self.get_qa_content()

    def refresh_all_content(self):
        """Refresh PDF preview and all right-side tab contents."""
        if not self.current_doc:
            empty = self._error("未选择文档")
            return empty, empty, empty, empty, empty

        return (
            self._pdf_output(),
            self.get_qa_content(),
            self.get_parsing_content(),
            self.get_serialization_content(),
            self.get_ingestion_content(),
        )

    # ------------------------------------------------------------------
    # Content builders
    # ------------------------------------------------------------------
    def get_parsing_content(self) -> str:
        if not self.current_doc:
            return self._error("未选择文档")

        parsing_data = self.loader.load_parsing_results(self.current_doc)
        if not parsing_data:
            return self._error("PDF解析数据不存在")

        metainfo = parsing_data.get("metainfo", {})
        pages = self._extract_pages(parsing_data)
        tables = parsing_data.get("tables", [])
        company_name = metainfo.get("company_name", "未知")
        actual_pages = len(pages)
        tables_count = len(tables)
        total_text_length = self._count_text_length_from_pages(pages)

        page_preview = []
        for page in pages[:2]:
            if isinstance(page, dict):
                blocks = page.get("content", [])
                page_preview.append(
                    {
                        "page": page.get("page", "未知"),
                        "blocks_count": len(blocks) if isinstance(blocks, list) else 0,
                        "first_blocks": blocks[:5] if isinstance(blocks, list) else str(blocks)[:500],
                    }
                )
            else:
                page_preview.append(str(page)[:500])

        table_preview = []
        for table in tables[:3]:
            if isinstance(table, dict):
                table_preview.append(
                    {
                        "table_id": table.get("table_id"),
                        "page": table.get("page"),
                        "rows": table.get("#-rows"),
                        "cols": table.get("#-cols"),
                        "markdown_preview": str(table.get("markdown", ""))[:600],
                    }
                )

        body = self._stats_grid(
            [
                ("公司名称", company_name),
                ("页面数量", f"{actual_pages} 页"),
                ("表格数量", f"{tables_count} 个"),
                ("文本长度", f"{total_text_length:,} 字符"),
            ]
        )
        body += "<h4>解析数据轻量预览</h4>"
        body += (
            "<pre class=\"data-preview-content\">"
            + self._json_preview({"metainfo": metainfo, "pages_preview": page_preview, "tables_preview": table_preview})
            + "</pre>"
        )
        return self._card("📄 PDF解析统计", body)

    def get_serialization_content(self) -> str:
        if not self.current_doc:
            return self._error("未选择文档")

        markdown_content = self.loader.load_markdown_content(self.current_doc)
        merged_data = self.loader.load_merged_results(self.current_doc)
        if not markdown_content and not merged_data:
            return self._error("序列化数据不存在")

        sections: list[str] = []
        if markdown_content:
            content_preview = markdown_content
            if len(content_preview) > 5000:
                content_preview = content_preview[:5000] + "\n\n... 内容过长，已截断"
            sections.append("<h4>Markdown格式报告</h4>")
            sections.append(f"<pre class=\"markdown-content\">{html.escape(content_preview)}</pre>")

        if merged_data:
            merged_preview = {
                "keys": list(merged_data.keys()) if isinstance(merged_data, dict) else None,
                "preview": merged_data,
            }
            sections.append("<h4>合并后的报告数据预览</h4>")
            sections.append(f"<pre class=\"data-preview-content\">{self._json_preview(merged_preview)}</pre>")

        return self._card("📘 表格序列化结果", "".join(sections))

    def get_ingestion_content(self) -> str:
        if not self.current_doc:
            return self._error("未选择文档")

        vector_stats = self.loader.get_vectorization_stats(self.current_doc)
        chunked_data = self.loader.load_chunked_results(self.current_doc)
        faiss_status = "✅ 存在" if vector_stats.get("faiss_exists") else "❌ 不存在"

        body = self._stats_grid(
            [
                ("FAISS向量库", faiss_status),
                ("向量库大小", f"{vector_stats.get('faiss_size_mb', 0)} MB"),
                ("切块总数", f"{vector_stats.get('total_chunks', 0)} 个"),
                ("总Token数", f"{vector_stats.get('total_tokens', 0):,}"),
                ("覆盖页数", f"{vector_stats.get('pages_with_chunks', 0)} 页"),
                ("平均每页切块", f"{vector_stats.get('chunks_per_page', 0)} 个"),
            ]
        )

        if chunked_data:
            chunks = chunked_data.get("content", {}).get("chunks", [])
            chunk_preview = {
                "document_id": chunked_data.get("document_id", self.current_doc),
                "total_chunks": len(chunks),
                "first_chunks": chunks[:5],
            }
            body += "<h4>切块数据轻量预览</h4>"
            body += f"<pre class=\"data-preview-content\">{self._json_preview(chunk_preview)}</pre>"
        else:
            body += "<p class=\"warning-text\">❌ 切块数据不存在</p>"

        return self._card("🧱 数据注入统计", body)

    def get_qa_content(self) -> str:
        if not self.current_doc:
            return self._error("未选择文档")

        qa_results = self.loader.load_qa_results(self.current_config)
        if not qa_results:
            return self._error(f"配置 '{self.current_config}' 的问答结果不存在")

        total_questions = len(qa_results)
        answered_questions = sum(
            1
            for qa in qa_results
            if qa.get("value") is not None and str(qa.get("value", "")).strip() and qa.get("value", "") != "N/A"
        )
        answered_pct = round(answered_questions / total_questions * 100, 1) if total_questions else 0

        type_stats: dict[str, int] = {}
        for qa in qa_results:
            qtype = str(qa.get("kind", "未知"))
            type_stats[qtype] = type_stats.get(qtype, 0) + 1
        type_stats_text = ", ".join([f"{html.escape(k)}({v})" for k, v in type_stats.items()])

        body = self._stats_grid(
            [
                ("问题总数", total_questions),
                ("已回答", f"{answered_questions} ({answered_pct}%)"),
                ("使用配置", self.current_config),
                ("问题类型", type_stats_text),
            ]
        )
        body += "<h4>详细问答结果（前10个）</h4>"

        detail_items = []
        for i, qa in enumerate(qa_results[:10]):
            question = html.escape(str(qa.get("question_text", "无问题")))
            value = qa.get("value")
            answer = html.escape(str(value) if value is not None else "无答案")
            references = qa.get("references", [])
            kind = html.escape(str(qa.get("kind", "未知")))

            error_info = qa.get("error", "")
            if error_info:
                error_preview = str(error_info)
                if len(error_preview) > 100:
                    error_preview = error_preview[:100] + "..."
                answer += f" (错误: {html.escape(error_preview)})"

            refs_text = "无引用"
            if references:
                refs_text = " | ".join([f"页面 {html.escape(str(ref.get('page_index', '?')))}" for ref in references[:3]])

            detail_items.append(
                f"""
                <div class="qa-detail-item">
                  <div class="qa-number">Q{i + 1}</div>
                  <div class="qa-content">
                    <div><strong>问题 ({kind})：</strong>{question}</div>
                    <div><strong>答案：</strong>{answer}</div>
                    <div><strong>引用：</strong>{len(references)} 个引用 {refs_text}</div>
                  </div>
                </div>
                """
            )

        body += "".join(detail_items)
        if len(qa_results) > 10:
            body += f"<p class=\"more-text\">... 还有 {len(qa_results) - 10} 个问答对</p>"

        return self._card("🎯 问答结果统计", body)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def create_interface(self):
        css = """
        .main-container { max-width: 1500px; margin: 0 auto; min-height: 100vh; }
        .config-panel { background: #eef6ff; padding: 10px; border-radius: 10px; margin-bottom: 16px; }
        .content-row { gap: 18px; align-items: stretch; }
        .pdf-column, .tabs-column { min-width: 0; }
        .content-card, .pdf-viewer-container, .error-card {
            background: #ffffff; color: #111827; border: 1px solid #e5e7eb;
            border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.10);
        }
        .content-card h3, .content-card h4, .pdf-viewer-container h3, .error-card h3 { color: #111827; margin-top: 0; }
        .content-card p, .content-card div, .pdf-viewer-container p, .pdf-viewer-container div, .error-card p { color: #111827; }
        .pdf-viewer-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
        .pdf-meta { color: #4b5563 !important; font-size: 13px; overflow-wrap: anywhere; }
        .pdf-meta-sep { margin: 0 8px; color: #9ca3af !important; }
        .pdf-download-link { display: inline-block; padding: 8px 12px; border-radius: 8px; background: #2563eb; color: #ffffff !important; text-decoration: none !important; white-space: nowrap; font-weight: 700; }
        .pdf-preview-frame { display: block; width: 100%; height: calc(100vh - 300px); min-height: 720px; border: 1px solid #d1d5db; border-radius: 8px; background: #f9fafb; }
        .pdf-fallback { margin: 10px 0 0 0; color: #4b5563 !important; font-size: 13px; }
        .tab-content { min-height: 760px; max-height: calc(100vh - 235px); overflow-y: auto; padding-right: 4px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; margin: 12px 0 16px 0; }
        .stat-item { padding: 10px 12px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; overflow-wrap: anywhere; }
        .stat-label { color: #6b7280 !important; font-size: 12px; margin-bottom: 4px; }
        .stat-value { color: #111827 !important; font-size: 15px; font-weight: 700; }
        .data-preview-content, .markdown-content { white-space: pre-wrap; background: #0f172a; color: #e5e7eb !important; padding: 12px; border-radius: 8px; overflow: auto; max-height: 460px; font-size: 13px; line-height: 1.45; }
        .qa-detail-item { display: flex; gap: 12px; margin: 12px 0; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fafafa; }
        .qa-number { width: 36px; height: 36px; flex: 0 0 36px; background: #2563eb; color: #ffffff !important; border-radius: 999px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
        .qa-content { line-height: 1.65; overflow-wrap: anywhere; }
        .error-card { color: #991b1b; background: #fef2f2; border-color: #fecaca; }
        .error-card h3, .error-card p, .error-text { color: #b91c1c !important; }
        .warning-text { color: #b45309 !important; }
        .more-text { color: #4b5563 !important; margin-top: 12px; }
        """

        initial_pdf, initial_qa, initial_parsing, initial_serialization, initial_ingestion = self.refresh_all_content()

        with gr.Blocks(title="RAG Challenge 复现结果可视化") as interface:
            gr.HTML(f"<style>{css}</style>")
            with gr.Column(elem_classes="main-container"):
                gr.Markdown("# 🏆 RAG Challenge 复现结果可视化")

                with gr.Row(elem_classes="config-panel"):
                    with gr.Column(scale=2):
                        doc_dropdown = gr.Dropdown(
                            choices=self.available_docs,
                            value=self.current_doc,
                            label="📄 选择文档",
                            info="选择要查看的PDF报告",
                        )
                    with gr.Column(scale=2):
                        config_dropdown = gr.Dropdown(
                            choices=self.available_configs,
                            value=self.current_config,
                            label="⚙️ 问答配置",
                            info="选择问答结果的配置版本",
                        )
                    with gr.Column(scale=1):
                        refresh_btn = gr.Button("🔄 刷新", variant="primary")

                with gr.Row(elem_classes="content-row"):
                    with gr.Column(scale=1, min_width=560, elem_classes="pdf-column"):
                        pdf_viewer = gr.HTML(initial_pdf, label="PDF预览")

                    with gr.Column(scale=1, min_width=520, elem_classes="tabs-column"):
                        with gr.Tabs():
                            with gr.Tab("🎯 问答结果"):
                                qa_content = gr.HTML(initial_qa, elem_classes="tab-content")
                            with gr.Tab("📄 PDF解析"):
                                parsing_content = gr.HTML(initial_parsing, elem_classes="tab-content")
                            with gr.Tab("🔄 序列化"):
                                serialization_content = gr.HTML(initial_serialization, elem_classes="tab-content")
                            with gr.Tab("🧱 数据注入"):
                                ingestion_content = gr.HTML(initial_ingestion, elem_classes="tab-content")

                outputs = [pdf_viewer, qa_content, parsing_content, serialization_content, ingestion_content]
                doc_dropdown.change(fn=self.update_document, inputs=[doc_dropdown], outputs=outputs)
                config_dropdown.change(fn=self.update_config, inputs=[config_dropdown], outputs=[qa_content])
                refresh_btn.click(fn=self.refresh_all_content, outputs=outputs)

        return interface


def create_fastapi_app(viz_app: RAGVisualizationApp, interface: gr.Blocks) -> FastAPI:
    """Create a FastAPI host with a dedicated inline-PDF route."""
    api = FastAPI()

    @api.get("/pdf/{doc_id}")
    def serve_pdf(doc_id: str):
        if doc_id not in viz_app.available_docs:
            raise HTTPException(status_code=404, detail="Unknown document id")

        pdf_path = (viz_app.data_path / "pdf_reports" / f"{doc_id}.pdf").resolve()
        if not pdf_path.exists() or not pdf_path.is_file():
            raise HTTPException(status_code=404, detail="PDF file not found")

        headers = {
            "Content-Disposition": f'inline; filename="{pdf_path.name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        }
        return FileResponse(str(pdf_path), media_type="application/pdf", filename=pdf_path.name, headers=headers)

    @api.get("/health")
    def health():
        return {"ok": True, "docs": len(viz_app.available_docs), "configs": len(viz_app.available_configs)}

    # Keep allowed_paths for Gradio-generated file URLs if future components need
    # them.  The PDF iframe itself uses /pdf/{doc_id}, so it does not depend on
    # Gradio's internal file-serving route.
    try:
        return gr.mount_gradio_app(api, interface, path="/", allowed_paths=[str(viz_app.data_path)])
    except TypeError:
        # Older Gradio versions may not expose allowed_paths on mount_gradio_app.
        return gr.mount_gradio_app(api, interface, path="/")


def main():
    """Entry point for the visualization app."""
    data_path = (current_dir / "../data/test_set").resolve()
    if not data_path.exists():
        print(f"❌ 数据目录不存在: {data_path}")
        print("请确保在正确的目录下运行，且数据已准备完毕")
        return

    print(f"✅ 数据目录: {data_path}")
    app = RAGVisualizationApp(str(data_path))
    if not app.available_docs:
        print("❌ 未找到可用的PDF文档")
        return

    print(f"✅ 找到 {len(app.available_docs)} 个文档: {app.available_docs}")
    print(f"✅ 找到 {len(app.available_configs)} 个配置: {app.available_configs}")
    print("✅ 使用 FastAPI /pdf/{doc_id} 路由 + 浏览器原生 PDF iframe 预览")

    interface = app.create_interface()
    fastapi_app = create_fastapi_app(app, interface)

    print("🚀 启动可视化界面...")
    print("🌐 界面地址: http://127.0.0.1:7860")
    print("🩺 健康检查: http://127.0.0.1:7860/health")
    uvicorn.run(fastapi_app, host="127.0.0.1", port=7860, log_level="info")


if __name__ == "__main__":
    main()
