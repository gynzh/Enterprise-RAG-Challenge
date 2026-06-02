"""RAG Challenge visualization app.

v4 fixes:
1. Keep the stable FastAPI /pdf/{doc_id} PDF route and iframe preview.
2. Render card/tab HTML with explicit light-card colors to avoid white text on
   white backgrounds in dark browser/Gradio themes.
3. Suppress routine Uvicorn access logs and reduce startup output.
"""

from __future__ import annotations

import html
import json
import logging
import sys
from pathlib import Path
from typing import Any, Iterable

import gradio as gr
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

from components.data_loader import RAGResultsLoader  # noqa: E402
from components.pdf_viewer import PDFViewer  # noqa: E402

APP_TITLE = "RAG Challenge \u590d\u73b0\u7ed3\u679c\u53ef\u89c6\u5316"


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

    @staticmethod
    def _json_preview(data: Any, limit: int = 8000) -> str:
        preview = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        if len(preview) > limit:
            preview = preview[:limit] + "\n\n... content truncated"
        return html.escape(preview)

    @staticmethod
    def _extract_pages(parsing_data: dict) -> list:
        content = parsing_data.get("content", [])
        if isinstance(content, list):
            return content
        if isinstance(content, dict):
            return content.get("pages", [])
        return []

    @staticmethod
    def _count_text_length_from_pages(pages: list) -> int:
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
        return (
            f'<section class="{css_class}">'
            f'<h3>{html.escape(title)}</h3>'
            f'{body_html}'
            '</section>'
        )

    @staticmethod
    def _error(message: str) -> str:
        return (
            '<section class="error-card">'
            '<h3>\u51fa\u9519</h3>'
            f'<p>{html.escape(message)}</p>'
            '</section>'
        )

    @staticmethod
    def _stats_grid(items: Iterable[tuple[str, Any]]) -> str:
        cells = []
        for label, value in items:
            cells.append(
                '<div class="stat-item">'
                f'<div class="stat-label">{html.escape(str(label))}</div>'
                f'<div class="stat-value">{html.escape(str(value))}</div>'
                '</div>'
            )
        return f'<div class="stats-grid">{"".join(cells)}</div>'

    @staticmethod
    def _pre(content: str, css_class: str = "data-preview-content") -> str:
        return f'<pre class="{css_class}">{content}</pre>'

    def _current_pdf_path(self) -> Path:
        return self.data_path / "pdf_reports" / f"{self.current_doc}.pdf"

    def _pdf_output(self) -> str:
        return PDFViewer.create_pdf_viewer(self._current_pdf_path(), self.current_doc).value

    def update_document(self, doc_id: str):
        self.current_doc = doc_id or ""
        return self.refresh_all_content()

    def update_config(self, config: str):
        self.current_config = config or ""
        return self.get_qa_content()

    def refresh_all_content(self):
        if not self.current_doc:
            empty = self._error("\u672a\u9009\u62e9\u6587\u6863")
            return empty, empty, empty, empty, empty
        return (
            self._pdf_output(),
            self.get_qa_content(),
            self.get_parsing_content(),
            self.get_serialization_content(),
            self.get_ingestion_content(),
        )

    def get_parsing_content(self) -> str:
        if not self.current_doc:
            return self._error("\u672a\u9009\u62e9\u6587\u6863")
        parsing_data = self.loader.load_parsing_results(self.current_doc)
        if not parsing_data:
            return self._error("PDF\u89e3\u6790\u6570\u636e\u4e0d\u5b58\u5728")

        metainfo = parsing_data.get("metainfo", {})
        pages = self._extract_pages(parsing_data)
        tables = parsing_data.get("tables", [])
        company_name = metainfo.get("company_name", "Unknown")
        actual_pages = len(pages)
        tables_count = len(tables)
        total_text_length = self._count_text_length_from_pages(pages)

        page_preview = []
        for page in pages[:2]:
            if isinstance(page, dict):
                blocks = page.get("content", [])
                page_preview.append(
                    {
                        "page": page.get("page", "?"),
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
                ("\u516c\u53f8\u540d\u79f0", company_name),
                ("\u9875\u9762\u6570\u91cf", f"{actual_pages} \u9875"),
                ("\u8868\u683c\u6570\u91cf", f"{tables_count} \u4e2a"),
                ("\u6587\u672c\u957f\u5ea6", f"{total_text_length:,} \u5b57\u7b26"),
            ]
        )
        body += '<h4>\u89e3\u6790\u6570\u636e\u8f7b\u91cf\u9884\u89c8</h4>'
        body += self._pre(self._json_preview({"metainfo": metainfo, "pages_preview": page_preview, "tables_preview": table_preview}))
        return self._card("PDF\u89e3\u6790\u7edf\u8ba1", body)

    def get_serialization_content(self) -> str:
        if not self.current_doc:
            return self._error("\u672a\u9009\u62e9\u6587\u6863")
        markdown_content = self.loader.load_markdown_content(self.current_doc)
        merged_data = self.loader.load_merged_results(self.current_doc)
        if not markdown_content and not merged_data:
            return self._error("\u5e8f\u5217\u5316\u6570\u636e\u4e0d\u5b58\u5728")

        sections: list[str] = []
        if markdown_content:
            content_preview = markdown_content
            if len(content_preview) > 5000:
                content_preview = content_preview[:5000] + "\n\n... content truncated"
            sections.append('<h4>Markdown\u683c\u5f0f\u62a5\u544a</h4>')
            sections.append(self._pre(html.escape(content_preview), "markdown-content"))
        if merged_data:
            merged_preview = {
                "keys": list(merged_data.keys()) if isinstance(merged_data, dict) else None,
                "preview": merged_data,
            }
            sections.append('<h4>\u5408\u5e76\u540e\u7684\u62a5\u544a\u6570\u636e\u9884\u89c8</h4>')
            sections.append(self._pre(self._json_preview(merged_preview)))
        return self._card("\u8868\u683c\u5e8f\u5217\u5316\u7ed3\u679c", "".join(sections))

    def get_ingestion_content(self) -> str:
        if not self.current_doc:
            return self._error("\u672a\u9009\u62e9\u6587\u6863")
        vector_stats = self.loader.get_vectorization_stats(self.current_doc)
        chunked_data = self.loader.load_chunked_results(self.current_doc)
        faiss_status = "\u5b58\u5728" if vector_stats.get("faiss_exists") else "\u4e0d\u5b58\u5728"
        body = self._stats_grid(
            [
                ("FAISS\u5411\u91cf\u5e93", faiss_status),
                ("\u5411\u91cf\u5e93\u5927\u5c0f", f"{vector_stats.get('faiss_size_mb', 0)} MB"),
                ("\u5207\u5757\u603b\u6570", f"{vector_stats.get('total_chunks', 0)} \u4e2a"),
                ("\u603bToken\u6570", f"{vector_stats.get('total_tokens', 0):,}"),
                ("\u8986\u76d6\u9875\u6570", f"{vector_stats.get('pages_with_chunks', 0)} \u9875"),
                ("\u5e73\u5747\u6bcf\u9875\u5207\u5757", f"{vector_stats.get('chunks_per_page', 0)} \u4e2a"),
            ]
        )
        if chunked_data:
            chunks = chunked_data.get("content", {}).get("chunks", [])
            chunk_preview = {
                "document_id": chunked_data.get("document_id", self.current_doc),
                "total_chunks": len(chunks),
                "first_chunks": chunks[:5],
            }
            body += '<h4>\u5207\u5757\u6570\u636e\u8f7b\u91cf\u9884\u89c8</h4>'
            body += self._pre(self._json_preview(chunk_preview))
        else:
            body += '<p class="warning-text">\u5207\u5757\u6570\u636e\u4e0d\u5b58\u5728</p>'
        return self._card("\u6570\u636e\u6ce8\u5165\u7edf\u8ba1", body)

    def get_qa_content(self) -> str:
        if not self.current_doc:
            return self._error("\u672a\u9009\u62e9\u6587\u6863")
        qa_results = self.loader.load_qa_results(self.current_config)
        if not qa_results:
            return self._error(f"\u914d\u7f6e '{self.current_config}' \u7684\u95ee\u7b54\u7ed3\u679c\u4e0d\u5b58\u5728")

        total_questions = len(qa_results)
        answered_questions = sum(
            1
            for qa in qa_results
            if qa.get("value") is not None and str(qa.get("value", "")).strip() and qa.get("value", "") != "N/A"
        )
        answered_pct = round(answered_questions / total_questions * 100, 1) if total_questions else 0
        type_stats: dict[str, int] = {}
        for qa in qa_results:
            qtype = str(qa.get("kind", "Unknown"))
            type_stats[qtype] = type_stats.get(qtype, 0) + 1
        type_stats_text = ", ".join([f"{html.escape(k)}({v})" for k, v in type_stats.items()])

        body = self._stats_grid(
            [
                ("\u95ee\u9898\u603b\u6570", total_questions),
                ("\u5df2\u56de\u7b54", f"{answered_questions} ({answered_pct}%)"),
                ("\u4f7f\u7528\u914d\u7f6e", self.current_config),
                ("\u95ee\u9898\u7c7b\u578b", type_stats_text),
            ]
        )
        body += '<h4>\u8be6\u7ec6\u95ee\u7b54\u7ed3\u679c\uff08\u524d10\u4e2a\uff09</h4>'
        detail_items = []
        for i, qa in enumerate(qa_results[:10]):
            question = html.escape(str(qa.get("question_text", "")))
            value = qa.get("value")
            answer = html.escape(str(value) if value is not None else "")
            references = qa.get("references", [])
            kind = html.escape(str(qa.get("kind", "Unknown")))
            error_info = qa.get("error", "")
            if error_info:
                error_preview = str(error_info)
                if len(error_preview) > 100:
                    error_preview = error_preview[:100] + "..."
                answer += f" <span class=\"error-text\">({html.escape(error_preview)})</span>"
            if references:
                refs_text = " | ".join([f"\u9875\u9762 {html.escape(str(ref.get('page_index', '?')))}" for ref in references[:3]])
            else:
                refs_text = "\u65e0\u5f15\u7528"
            detail_items.append(
                '<div class="qa-detail-item">'
                f'<div class="qa-number">Q{i + 1}</div>'
                '<div class="qa-content">'
                f'<div><strong>\u95ee\u9898 ({kind})\uff1a</strong>{question}</div>'
                f'<div><strong>\u7b54\u6848\uff1a</strong>{answer}</div>'
                f'<div><strong>\u5f15\u7528\uff1a</strong>{len(references)} \u4e2a\u5f15\u7528 {refs_text}</div>'
                '</div>'
                '</div>'
            )
        body += "".join(detail_items)
        if len(qa_results) > 10:
            body += f'<p class="more-text">... \u8fd8\u6709 {len(qa_results) - 10} \u4e2a\u95ee\u7b54\u5bf9</p>'
        return self._card("\u95ee\u7b54\u7ed3\u679c\u7edf\u8ba1", body)

    def create_interface(self):
        css = """
        :root { color-scheme: dark; }
        .gradio-container { background: #07111f !important; }
        #rag-viz-root { max-width: 1500px; margin: 0 auto; min-height: 100vh; color: #e5e7eb; }
        #rag-viz-root h1 { color: #f8fafc !important; }
        #rag-viz-root .config-panel { background: #eef6ff; padding: 10px; border-radius: 10px; margin-bottom: 16px; }
        #rag-viz-root .config-panel label, #rag-viz-root .config-panel span, #rag-viz-root .config-panel .info { color: #111827 !important; }
        #rag-viz-root .config-panel input, #rag-viz-root .config-panel textarea, #rag-viz-root .config-panel [role="button"] { color: #f8fafc !important; }
        #rag-viz-root .content-row { gap: 18px; align-items: stretch; }
        #rag-viz-root .pdf-column, #rag-viz-root .tabs-column { min-width: 0; }
        #rag-viz-root .content-card, #rag-viz-root .pdf-viewer-container, #rag-viz-root .error-card {
            background: #ffffff !important; color: #111827 !important; border: 1px solid #e5e7eb;
            border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.10);
        }
        #rag-viz-root .content-card h3, #rag-viz-root .content-card h4,
        #rag-viz-root .pdf-viewer-container h3, #rag-viz-root .pdf-viewer-container h4,
        #rag-viz-root .error-card h3 { color: #111827 !important; margin-top: 0; }
        #rag-viz-root .content-card p, #rag-viz-root .content-card div,
        #rag-viz-root .content-card span, #rag-viz-root .content-card strong,
        #rag-viz-root .pdf-viewer-container p, #rag-viz-root .pdf-viewer-container div,
        #rag-viz-root .pdf-viewer-container span, #rag-viz-root .pdf-viewer-container strong,
        #rag-viz-root .error-card p, #rag-viz-root .error-card div, #rag-viz-root .error-card span {
            color: #111827 !important;
        }
        #rag-viz-root .tabs-column [role="tab"], #rag-viz-root .tabs-column button { color: #e5e7eb !important; }
        #rag-viz-root .tabs-column [aria-selected="true"] { color: #60a5fa !important; }
        #rag-viz-root .tab-content { min-height: 760px; max-height: calc(100vh - 235px); overflow-y: auto; padding-right: 4px; }
        #rag-viz-root .pdf-viewer-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
        #rag-viz-root .pdf-meta { color: #4b5563 !important; font-size: 13px; overflow-wrap: anywhere; }
        #rag-viz-root .pdf-meta code { color: #111827 !important; background: #f3f4f6; padding: 1px 4px; border-radius: 4px; }
        #rag-viz-root .pdf-download-link { display: inline-block; padding: 8px 12px; border-radius: 8px; background: #2563eb; color: #ffffff !important; text-decoration: none !important; white-space: nowrap; font-weight: 700; }
        #rag-viz-root .pdf-preview-frame { display: block; width: 100%; height: calc(100vh - 300px); min-height: 720px; border: 1px solid #d1d5db; border-radius: 8px; background: #f9fafb; }
        #rag-viz-root .pdf-fallback { margin: 10px 0 0 0; color: #4b5563 !important; font-size: 13px; }
        #rag-viz-root .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; margin: 12px 0 16px 0; }
        #rag-viz-root .stat-item { padding: 10px 12px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; overflow-wrap: anywhere; }
        #rag-viz-root .stat-label { color: #6b7280 !important; font-size: 12px; margin-bottom: 4px; }
        #rag-viz-root .stat-value { color: #111827 !important; font-size: 15px; font-weight: 700; }
        #rag-viz-root .data-preview-content, #rag-viz-root .markdown-content {
            white-space: pre-wrap; background: #0f172a !important; color: #e5e7eb !important;
            padding: 12px; border-radius: 8px; overflow: auto; max-height: 460px; font-size: 13px; line-height: 1.45;
        }
        #rag-viz-root .qa-detail-item { display: flex; gap: 12px; margin: 12px 0; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fafafa; }
        #rag-viz-root .qa-number { width: 36px; height: 36px; flex: 0 0 36px; background: #2563eb; color: #ffffff !important; border-radius: 999px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
        #rag-viz-root .qa-content { line-height: 1.65; overflow-wrap: anywhere; }
        #rag-viz-root .error-card { color: #991b1b !important; background: #fef2f2 !important; border-color: #fecaca; }
        #rag-viz-root .error-card h3, #rag-viz-root .error-card p, #rag-viz-root .error-text { color: #b91c1c !important; }
        #rag-viz-root .warning-text { color: #b45309 !important; }
        #rag-viz-root .more-text { color: #4b5563 !important; margin-top: 12px; }
        """
        initial_pdf, initial_qa, initial_parsing, initial_serialization, initial_ingestion = self.refresh_all_content()

        with gr.Blocks(title=APP_TITLE) as interface:
            gr.HTML(f"<style>{css}</style>")
            with gr.Column(elem_id="rag-viz-root"):
                gr.Markdown(f"# {APP_TITLE}")
                with gr.Row(elem_classes="config-panel"):
                    with gr.Column(scale=2):
                        doc_dropdown = gr.Dropdown(
                            choices=self.available_docs,
                            value=self.current_doc,
                            label="\u9009\u62e9\u6587\u6863",
                            info="\u9009\u62e9\u8981\u67e5\u770b\u7684PDF\u62a5\u544a",
                        )
                    with gr.Column(scale=2):
                        config_dropdown = gr.Dropdown(
                            choices=self.available_configs,
                            value=self.current_config,
                            label="\u95ee\u7b54\u914d\u7f6e",
                            info="\u9009\u62e9\u95ee\u7b54\u7ed3\u679c\u7684\u914d\u7f6e\u7248\u672c",
                        )
                    with gr.Column(scale=1):
                        refresh_btn = gr.Button("\u5237\u65b0", variant="primary")

                with gr.Row(elem_classes="content-row"):
                    with gr.Column(scale=1, min_width=560, elem_classes="pdf-column"):
                        pdf_viewer = gr.HTML(initial_pdf, label="PDF\u9884\u89c8")
                    with gr.Column(scale=1, min_width=520, elem_classes="tabs-column"):
                        with gr.Tabs():
                            with gr.Tab("\u95ee\u7b54\u7ed3\u679c"):
                                qa_content = gr.HTML(initial_qa, elem_classes="tab-content")
                            with gr.Tab("PDF\u89e3\u6790"):
                                parsing_content = gr.HTML(initial_parsing, elem_classes="tab-content")
                            with gr.Tab("\u5e8f\u5217\u5316"):
                                serialization_content = gr.HTML(initial_serialization, elem_classes="tab-content")
                            with gr.Tab("\u6570\u636e\u6ce8\u5165"):
                                ingestion_content = gr.HTML(initial_ingestion, elem_classes="tab-content")

                outputs = [pdf_viewer, qa_content, parsing_content, serialization_content, ingestion_content]
                doc_dropdown.change(fn=self.update_document, inputs=[doc_dropdown], outputs=outputs)
                config_dropdown.change(fn=self.update_config, inputs=[config_dropdown], outputs=[qa_content])
                refresh_btn.click(fn=self.refresh_all_content, outputs=outputs)
        return interface


def create_fastapi_app(viz_app: RAGVisualizationApp, interface: gr.Blocks) -> FastAPI:
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

    try:
        return gr.mount_gradio_app(api, interface, path="/", allowed_paths=[str(viz_app.data_path)])
    except TypeError:
        return gr.mount_gradio_app(api, interface, path="/")


def main() -> None:
    data_path = (current_dir / "../data/test_set").resolve()
    if not data_path.exists():
        print(f"ERROR: data directory not found: {data_path}")
        print("Run this from codebase or check data/test_set.")
        return

    app = RAGVisualizationApp(str(data_path))
    if not app.available_docs:
        print("ERROR: no PDF documents found in data/test_set/pdf_reports.")
        return

    interface = app.create_interface()
    fastapi_app = create_fastapi_app(app, interface)

    print("RAG visualization ready")
    print(f"Data: {data_path}")
    print(f"Docs: {len(app.available_docs)} | Configs: {len(app.available_configs)}")
    print("Open: http://127.0.0.1:7860")
    print("Health: http://127.0.0.1:7860/health")
    print("Press Ctrl+C to stop")

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=7860,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
