import html
import json
import sys
from pathlib import Path
from typing import Any

import gradio as gr

# 添加组件模块到路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from components.data_loader import RAGResultsLoader
from components.pdf_viewer import PDFViewer


class RAGVisualizationApp:
    """RAG Challenge复现结果可视化应用。"""

    def __init__(self, data_path: str = "../data/test_set"):
        data_path_obj = Path(data_path)
        if not data_path_obj.is_absolute():
            data_path_obj = current_dir / data_path_obj

        self.data_path = data_path_obj.resolve()
        self.loader = RAGResultsLoader(str(self.data_path))

        self.available_docs = self.loader.get_available_documents()
        self.available_configs = self.loader.get_available_configs()

        self.current_doc = self.available_docs[0] if self.available_docs else ""
        self.current_config = (
            self.available_configs[0] if self.available_configs else "gemini_thinking_fc"
        )

    @staticmethod
    def _to_html(value: Any) -> str:
        """将 gr.HTML 组件或普通字符串统一转换成 HTML 字符串。"""
        if isinstance(value, str):
            return value
        component_value = getattr(value, "value", None)
        if component_value is not None:
            return component_value
        return str(value)

    @staticmethod
    def _json_preview(data: Any, limit: int = 8000) -> str:
        """生成安全的 JSON 预览文本。"""
        preview = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        if len(preview) > limit:
            preview = preview[:limit] + "\n\n... 内容过长，已截断"
        return html.escape(preview)

    @staticmethod
    def _extract_pages(parsing_data: dict) -> list:
        """从解析结果中提取页面列表，兼容 content 为 list 或 dict 的情况。"""
        content = parsing_data.get("content", [])
        if isinstance(content, list):
            return content
        if isinstance(content, dict):
            return content.get("pages", [])
        return []

    @staticmethod
    def _count_text_length_from_pages(pages: list) -> int:
        """统计解析结果中的文本长度。"""
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
    def _error(message: str) -> str:
        return f"<div class='error-card'>❌ {html.escape(message)}</div>"

    def update_document(self, doc_id: str):
        """更新当前选择的文档，并一次性刷新所有 Tab 内容。"""
        self.current_doc = doc_id or ""
        return self.refresh_all_content()

    def update_config(self, config: str):
        """更新当前选择的配置，并刷新问答内容。"""
        self.current_config = config or ""
        return self.get_qa_content()

    def refresh_all_content(self):
        """
        刷新主要内容。

        这里不再依赖 Tab.select 懒加载。部分 Gradio 版本/浏览器组合下，
        Tab.select 事件可能不触发，导致右侧三个 Tab 看起来“点击无响应”。
        因此页面加载、切换文档和点击刷新时直接准备好所有 Tab 内容。
        """
        if not self.current_doc:
            empty = self._error("未选择文档")
            return empty, empty, empty, empty, empty

        pdf_path = self.data_path / "pdf_reports" / f"{self.current_doc}.pdf"
        pdf_viewer = self._to_html(
            PDFViewer.create_pdf_viewer(str(pdf_path), self.current_doc)
        )

        return (
            pdf_viewer,
            self.get_parsing_content(),
            self.get_serialization_content(),
            self.get_ingestion_content(),
            self.get_qa_content(),
        )

    def get_parsing_content(self):
        """获取 PDF 解析阶段内容。"""
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
                        "first_blocks": blocks[:5]
                        if isinstance(blocks, list)
                        else str(blocks)[:500],
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

        preview_data = {
            "metainfo": metainfo,
            "pages_preview": page_preview,
            "tables_preview": table_preview,
        }

        return f"""
        <div class="content-card">
            <h3>📄 PDF解析统计</h3>
            <div class="stats-grid">
                <div class="stat-item"><strong>公司名称</strong><br>{html.escape(str(company_name))}</div>
                <div class="stat-item"><strong>页面数量</strong><br>{actual_pages} 页</div>
                <div class="stat-item"><strong>表格数量</strong><br>{tables_count} 个</div>
                <div class="stat-item"><strong>文本长度</strong><br>{total_text_length:,} 字符</div>
            </div>
            <h4>解析数据轻量预览</h4>
            <pre class="data-preview-content">{self._json_preview(preview_data)}</pre>
        </div>
        """

    def get_serialization_content(self):
        """获取序列化阶段内容。"""
        if not self.current_doc:
            return self._error("未选择文档")

        markdown_content = self.loader.load_markdown_content(self.current_doc)
        merged_data = self.loader.load_merged_results(self.current_doc)

        if not markdown_content and not merged_data:
            return self._error("序列化数据不存在")

        sections = ["<div class='content-card'><h3>🧾 表格序列化结果</h3>"]

        if markdown_content:
            content_preview = markdown_content
            if len(content_preview) > 5000:
                content_preview = content_preview[:5000] + "\n\n... 内容过长，已截断"
            sections.append(
                "<h4>Markdown格式报告</h4>"
                f"<pre class='markdown-content'>{html.escape(content_preview)}</pre>"
            )

        if merged_data:
            merged_preview = {
                "keys": list(merged_data.keys()) if isinstance(merged_data, dict) else None,
                "preview": merged_data,
            }
            sections.append(
                "<h4>合并后的报告数据预览</h4>"
                f"<pre class='data-preview-content'>{self._json_preview(merged_preview)}</pre>"
            )

        sections.append("</div>")
        return "".join(sections)

    def get_ingestion_content(self):
        """获取数据注入阶段内容。"""
        if not self.current_doc:
            return self._error("未选择文档")

        vector_stats = self.loader.get_vectorization_stats(self.current_doc)
        chunked_data = self.loader.load_chunked_results(self.current_doc)

        if chunked_data:
            chunks = chunked_data.get("content", {}).get("chunks", [])
            chunk_preview = {
                "document_id": chunked_data.get("document_id", self.current_doc),
                "total_chunks": len(chunks),
                "first_chunks": chunks[:5],
            }
            chunk_preview_html = (
                "<h4>切块数据轻量预览</h4>"
                f"<pre class='data-preview-content'>{self._json_preview(chunk_preview)}</pre>"
            )
        else:
            chunk_preview_html = "<p>❌ 切块数据不存在</p>"

        faiss_status = "✅ 存在" if vector_stats.get("faiss_exists") else "❌ 不存在"
        return f"""
        <div class="content-card">
            <h3>🗃️ 数据注入统计</h3>
            <div class="stats-grid">
                <div class="stat-item"><strong>FAISS向量库</strong><br>{faiss_status}</div>
                <div class="stat-item"><strong>向量库大小</strong><br>{vector_stats.get('faiss_size_mb', 0)} MB</div>
                <div class="stat-item"><strong>切块总数</strong><br>{vector_stats.get('total_chunks', 0)} 个</div>
                <div class="stat-item"><strong>总Token数</strong><br>{vector_stats.get('total_tokens', 0):,}</div>
                <div class="stat-item"><strong>覆盖页数</strong><br>{vector_stats.get('pages_with_chunks', 0)} 页</div>
                <div class="stat-item"><strong>平均每页切块</strong><br>{vector_stats.get('chunks_per_page', 0)} 个</div>
            </div>
            {chunk_preview_html}
        </div>
        """

    def get_qa_content(self):
        """获取问答阶段内容。"""
        if not self.current_doc:
            return self._error("未选择文档")

        qa_results = self.loader.load_qa_results(self.current_config)
        if not qa_results:
            return self._error(f"配置 '{self.current_config}' 的问答结果不存在")

        total_questions = len(qa_results)
        answered_questions = sum(
            1
            for qa in qa_results
            if qa.get("value") is not None
            and str(qa.get("value", "")).strip()
            and qa.get("value", "") != "N/A"
        )

        type_stats = {}
        for qa in qa_results:
            qtype = qa.get("kind", "未知")
            type_stats[qtype] = type_stats.get(qtype, 0) + 1

        details = []
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
                answer += f" <span class='error-text'>(错误: {html.escape(error_preview)})</span>"

            refs_text = "无引用"
            if references:
                refs_text = " | ".join(
                    [f"页面 {html.escape(str(ref.get('page_index', '?')))}" for ref in references[:3]]
                )

            details.append(
                f"""
                <div class="qa-detail-item">
                    <div class="qa-number">Q{i + 1}</div>
                    <div class="qa-content">
                        <div><strong>问题 ({kind}):</strong> {question}</div>
                        <div><strong>答案:</strong> {answer}</div>
                        <div><strong>引用:</strong> {len(references)} 个引用 {refs_text}</div>
                    </div>
                </div>
                """
            )

        more = ""
        if len(qa_results) > 10:
            more = f"<p><em>... 还有 {len(qa_results) - 10} 个问答对</em></p>"

        type_stats_text = ", ".join([f"{html.escape(str(k))}({v})" for k, v in type_stats.items()])
        answered_pct = round(answered_questions / total_questions * 100, 1) if total_questions else 0

        return f"""
        <div class="content-card qa-results">
            <h3>🎯 问答结果统计</h3>
            <div class="stats-grid">
                <div class="stat-item"><strong>问题总数</strong><br>{total_questions}</div>
                <div class="stat-item"><strong>已回答</strong><br>{answered_questions} ({answered_pct}%)</div>
                <div class="stat-item"><strong>使用配置</strong><br>{html.escape(str(self.current_config))}</div>
                <div class="stat-item"><strong>问题类型</strong><br>{type_stats_text}</div>
            </div>
            <h4>详细问答结果（前10个）</h4>
            {''.join(details)}
            {more}
        </div>
        """

    def create_interface(self):
        """创建 Gradio 界面。"""
        css = """
        .main-container {
            max-width: 1500px;
            margin: 0 auto;
            min-height: 100vh;
        }
        .config-panel {
            background: #f0f8ff;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .content-row {
            gap: 15px;
            align-items: stretch;
        }
        .pdf-column, .tabs-column {
            min-width: 0;
        }
        .pdf-viewer-container, .content-card, .error-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 14px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
        }
        .pdf-viewer-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
        }
        .pdf-viewer-header h3 {
            margin: 0 0 4px 0;
        }
        .pdf-meta {
            color: #4b5563;
            font-size: 13px;
        }
        .pdf-meta-sep {
            margin: 0 8px;
            color: #9ca3af;
        }
        .pdf-download-link {
            display: inline-block;
            padding: 8px 12px;
            border-radius: 8px;
            background: #2563eb;
            color: white !important;
            text-decoration: none !important;
            white-space: nowrap;
            font-weight: 600;
        }
        .pdf-preview-frame {
            width: 100%;
            height: calc(100vh - 265px);
            min-height: 720px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            background: #f9fafb;
        }
        .pdf-fallback {
            margin-top: 8px;
            color: #6b7280;
            font-size: 13px;
        }
        .tab-content {
            min-height: 720px;
            max-height: calc(100vh - 220px);
            overflow-y: auto;
            padding-right: 4px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin: 12px 0 16px 0;
        }
        .stat-item {
            padding: 10px;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow-wrap: anywhere;
        }
        .data-preview-content, .markdown-content {
            white-space: pre-wrap;
            background: #0f172a;
            color: #e5e7eb;
            padding: 12px;
            border-radius: 8px;
            overflow: auto;
            max-height: 460px;
            font-size: 13px;
            line-height: 1.45;
        }
        .qa-detail-item {
            display: flex;
            gap: 12px;
            margin: 12px 0;
            padding: 12px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background: #fafafa;
        }
        .qa-number {
            width: 36px;
            height: 36px;
            flex: 0 0 36px;
            background: #2563eb;
            color: white;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
        }
        .qa-content {
            line-height: 1.65;
        }
        .error-card {
            color: #b91c1c;
            background: #fef2f2;
            border-color: #fecaca;
        }
        .error-text {
            color: #b91c1c;
        }
        """

        with gr.Blocks(
            title="RAG Challenge 复现结果可视化",
            theme=gr.themes.Soft(primary_hue="blue"),
            css=css,
        ) as interface:
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
                    with gr.Column(scale=1, elem_classes="pdf-column"):
                        pdf_viewer = gr.HTML(
                            "<p>PDF文档将在此显示...</p>",
                            label="PDF预览",
                            elem_classes="pdf-viewer-html",
                        )

                    with gr.Column(scale=1, elem_classes="tabs-column"):
                        with gr.Tabs():
                            with gr.Tab("🎯 问答结果"):
                                qa_content = gr.HTML(
                                    "<p>问答结果将在此显示...</p>",
                                    elem_classes="tab-content",
                                )
                            with gr.Tab("📄 PDF解析"):
                                parsing_content = gr.HTML(
                                    "<p>PDF解析结果将在此显示...</p>",
                                    elem_classes="tab-content",
                                )
                            with gr.Tab("🔄 序列化"):
                                serialization_content = gr.HTML(
                                    "<p>序列化结果将在此显示...</p>",
                                    elem_classes="tab-content",
                                )
                            with gr.Tab("🗃️ 数据注入"):
                                ingestion_content = gr.HTML(
                                    "<p>数据注入结果将在此显示...</p>",
                                    elem_classes="tab-content",
                                )

                doc_dropdown.change(
                    fn=self.update_document,
                    inputs=[doc_dropdown],
                    outputs=[
                        pdf_viewer,
                        parsing_content,
                        serialization_content,
                        ingestion_content,
                        qa_content,
                    ],
                )
                config_dropdown.change(
                    fn=self.update_config,
                    inputs=[config_dropdown],
                    outputs=[qa_content],
                )
                refresh_btn.click(
                    fn=self.refresh_all_content,
                    outputs=[
                        pdf_viewer,
                        parsing_content,
                        serialization_content,
                        ingestion_content,
                        qa_content,
                    ],
                )
                interface.load(
                    fn=self.refresh_all_content,
                    outputs=[
                        pdf_viewer,
                        parsing_content,
                        serialization_content,
                        ingestion_content,
                        qa_content,
                    ],
                )

        return interface


def main():
    """主函数。"""
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

    interface = app.create_interface()
    print("🚀 启动可视化界面...")
    print("📱 界面地址: http://127.0.0.1:7860")
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
