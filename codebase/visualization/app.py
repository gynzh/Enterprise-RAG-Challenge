import gradio as gr
import sys
import json
import html
from pathlib import Path

# 添加组件模块到路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from components.data_loader import RAGResultsLoader
from components.pdf_viewer import PDFViewer
from components.json_viewer import JSONViewer


class RAGVisualizationApp:
    """RAG Challenge复现结果可视化应用"""
    
    def __init__(self, data_path: str = "../data/test_set"):
        """
        初始化应用
        
        Args:
            data_path: 数据目录路径
        """
        self.data_path = Path(current_dir) / data_path
        self.loader = RAGResultsLoader(str(self.data_path))
        
        # 获取可用文档和配置
        self.available_docs = self.loader.get_available_documents()
        self.available_configs = self.loader.get_available_configs()
        
        # 当前选择的文档和配置
        self.current_doc = self.available_docs[0] if self.available_docs else ""
        self.current_config = self.available_configs[0] if self.available_configs else "gemini_thinking_fc"

    @staticmethod
    def _to_html(value):
        """
        将 gr.HTML 组件或普通字符串统一转换成 HTML 字符串。
        Gradio 事件回调的输出应该返回字符串，而不是返回新的 gr.HTML 组件。
        """
        if isinstance(value, str):
            return value

        component_value = getattr(value, "value", None)
        if component_value is not None:
            return component_value

        return str(value)

    @staticmethod
    def _placeholder(title: str) -> str:
        """懒加载占位内容"""
        safe_title = html.escape(title)
        return f"""
        <div class='lazy-placeholder'>
            <p>⏳ {safe_title} 尚未加载。</p>
            <p>点击该标签页后会自动加载内容。</p>
        </div>
        """

    @staticmethod
    def _json_preview(data, limit: int = 8000) -> str:
        """
        生成安全的 JSON 预览文本。
        注意：这里先截断，再 html.escape，避免大 JSON 直接塞进页面。
        """
        preview = json.dumps(data, ensure_ascii=False, indent=2, default=str)

        if len(preview) > limit:
            preview = preview[:limit] + "\n\n... 内容过长，已截断"

        return html.escape(preview)

    @staticmethod
    def _extract_pages(parsing_data):
        """从解析结果中提取页面列表，兼容 content 为 list 或 dict 的情况"""
        content = parsing_data.get("content", [])

        if isinstance(content, list):
            return content

        if isinstance(content, dict):
            return content.get("pages", [])

        return []

    @staticmethod
    def _count_text_length_from_pages(pages) -> int:
        """
        统计解析结果中的文本长度。
        你的 parsed json 中 page['content'] 是一个 block 列表，
        每个 block 里通常有 text 字段，所以不能只看 page['text']。
        """
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

    def update_document(self, doc_id: str):
        """更新当前选择的文档"""
        self.current_doc = doc_id
        return self.refresh_all_content()
    
    def update_config(self, config: str):
        """更新当前选择的配置"""
        self.current_config = config
        return self.refresh_qa_content()

    def refresh_all_content(self):
        """
        刷新主要内容。

        页面初始只加载 PDF 和问答结果。
        其他 Tab 等用户点击时再加载。
        """
        if not self.current_doc:
            empty = "<p>❌ 未选择文档</p>"
            return empty, empty, empty, empty, empty

        pdf_path = self.data_path / "pdf_reports" / f"{self.current_doc}.pdf"
        pdf_viewer = self._to_html(
            PDFViewer.create_pdf_viewer(str(pdf_path), self.current_doc)
        )

        qa_content = self.get_qa_content()

        return (
            pdf_viewer,
            self._placeholder("PDF解析结果"),
            self._placeholder("序列化结果"),
            self._placeholder("数据注入结果"),
            qa_content,
        )
    
    def refresh_qa_content(self):
        """仅刷新问答内容"""
        return self.get_qa_content()

    def get_parsing_content(self):
        """获取PDF解析阶段内容"""
        if not self.current_doc:
            return "<p>❌ 未选择文档</p>"

        parsing_data = self.loader.load_parsing_results(self.current_doc)

        if not parsing_data:
            return "<p>❌ PDF解析数据不存在</p>"

        metainfo = parsing_data.get("metainfo", {})
        pages = self._extract_pages(parsing_data)
        tables = parsing_data.get("tables", [])

        company_name = metainfo.get("company_name", "未知")
        actual_pages = len(pages)
        tables_count = len(tables)
        total_text_length = self._count_text_length_from_pages(pages)

        # 只构造轻量预览，不再把整个 parsing_data 转成字符串
        page_preview = []
        for page in pages[:2]:
            if isinstance(page, dict):
                blocks = page.get("content", [])
                page_preview.append({
                    "page": page.get("page", "未知"),
                    "blocks_count": len(blocks) if isinstance(blocks, list) else 0,
                    "first_blocks": blocks[:5] if isinstance(blocks, list) else str(blocks)[:500],
                })
            else:
                page_preview.append(str(page)[:500])

        table_preview = []
        for table in tables[:3]:
            if isinstance(table, dict):
                table_preview.append({
                    "table_id": table.get("table_id"),
                    "page": table.get("page"),
                    "rows": table.get("#-rows"),
                    "cols": table.get("#-cols"),
                    "markdown_preview": str(table.get("markdown", ""))[:600],
                })

        preview_data = {
            "metainfo": metainfo,
            "pages_preview": page_preview,
            "tables_preview": table_preview,
        }

        preview_text = self._json_preview(preview_data, limit=8000)

        stats_html = f"""
        <div class='parsing-container'>
            <div class='parsing-stats'>
                <h3>📊 PDF解析统计</h3>
                <div class='stats-grid'>
                    <div class='stat-item'>
                        <strong>公司名称:</strong> {html.escape(str(company_name))}
                    </div>
                    <div class='stat-item'>
                        <strong>页面数量:</strong> {actual_pages} 页
                    </div>
                    <div class='stat-item'>
                        <strong>表格数量:</strong> {tables_count} 个
                    </div>
                    <div class='stat-item'>
                        <strong>文本长度:</strong> {total_text_length:,} 字符
                    </div>
                </div>
            </div>

            <div class='parsing-preview'>
                <h4>📝 解析数据轻量预览</h4>
                <pre class='data-preview-content'>{preview_text}</pre>
            </div>
        </div>

        <style>
            .parsing-container {{
                display: flex;
                flex-direction: column;
                height: 100%;
            }}

            .parsing-stats {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 10px 0;
            }}

            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 15px 0;
            }}

            .stat-item {{
                padding: 10px;
                background: #f0f8ff;
                border-radius: 6px;
            }}

            .parsing-preview {{
                margin-top: 20px;
                flex: 1;
                display: flex;
                flex-direction: column;
            }}

            .data-preview-content {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                overflow-y: auto;
                flex: 1;
                min-height: 400px;
                max-height: 600px;
                font-size: 12px;
                line-height: 1.4;
                white-space: pre-wrap;
                word-wrap: break-word;
                font-family: 'Courier New', monospace;
            }}
        </style>
        """

        return stats_html
    
    def get_serialization_content(self):
        """获取序列化阶段内容"""
        if not self.current_doc:
            return "<p>❌ 未选择文档</p>"
        
        # 加载Markdown内容
        markdown_content = self.loader.load_markdown_content(self.current_doc)
        merged_data = self.loader.load_merged_results(self.current_doc)
        
        if not markdown_content and not merged_data:
            return "<p>❌ 序列化数据不存在</p>"
        
        html_content = """
        <div class='serialization-content'>
            <h3>🔄 表格序列化结果</h3>
        """
        
        if markdown_content:
            # 截断过长的内容
            if len(markdown_content) > 5000:
                content_preview = markdown_content[:5000] + "\n\n... (内容过长，已截断)"
            else:
                content_preview = markdown_content
            
            html_content += f"""
            <div class='markdown-section'>
                <h4>📝 Markdown格式报告</h4>
                <div class='markdown-content'>
                    <pre style='white-space: pre-wrap; background: #f8f9fa; padding: 15px; border-radius: 8px; max-height: 400px; overflow-y: auto;'>{content_preview}</pre>
                </div>
            </div>
            """
        
        if merged_data:
            json_component = JSONViewer.create_json_viewer_interface(
                merged_data,
                "🔗 合并后的报告数据"
            )
            html_content += f"""
            <div class='json-section'>
                <hr style='margin: 20px 0;'>
                {json_component.value if hasattr(json_component, 'value') else str(json_component)}
            </div>
            """
        
        html_content += "</div>"
        
        return html_content

    def get_ingestion_content(self):
        """获取数据注入阶段内容"""
        if not self.current_doc:
            return "<p>❌ 未选择文档</p>"

        vector_stats = self.loader.get_vectorization_stats(self.current_doc)
        chunked_data = self.loader.load_chunked_results(self.current_doc)

        if chunked_data:
            chunks = chunked_data.get("content", {}).get("chunks", [])
            chunk_preview = {
                "document_id": chunked_data.get("document_id", self.current_doc),
                "total_chunks": len(chunks),
                "first_chunks": chunks[:5],
            }
            chunk_preview_html = f"""
            <div class='chunk-preview'>
                <h4>🧩 切块数据轻量预览</h4>
                <pre class='data-preview-content'>{self._json_preview(chunk_preview, limit=8000)}</pre>
            </div>
            """
        else:
            chunk_preview_html = "<p>❌ 切块数据不存在</p>"

        html_content = f"""
        <div class='ingestion-container'>
            <div class='ingestion-stats'>
                <h3>💾 数据注入统计</h3>
                <div class='stats-grid'>
                    <div class='stat-item'>
                        <strong>FAISS向量库:</strong> {'✅ 存在' if vector_stats.get('faiss_exists') else '❌ 不存在'}
                    </div>
                    <div class='stat-item'>
                        <strong>向量库大小:</strong> {vector_stats.get('faiss_size_mb', 0)} MB
                    </div>
                    <div class='stat-item'>
                        <strong>切块总数:</strong> {vector_stats.get('total_chunks', 0)} 个
                    </div>
                    <div class='stat-item'>
                        <strong>总Token数:</strong> {vector_stats.get('total_tokens', 0):,}
                    </div>
                    <div class='stat-item'>
                        <strong>覆盖页数:</strong> {vector_stats.get('pages_with_chunks', 0)} 页
                    </div>
                    <div class='stat-item'>
                        <strong>平均每页切块:</strong> {vector_stats.get('chunks_per_page', 0)} 个
                    </div>
                </div>
            </div>

            {chunk_preview_html}
        </div>

        <style>
            .ingestion-container {{
                display: flex;
                flex-direction: column;
                height: 100%;
            }}

            .ingestion-stats {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 10px 0;
            }}

            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 15px 0;
            }}

            .stat-item {{
                padding: 10px;
                background: #f0f8ff;
                border-radius: 6px;
            }}

            .chunk-preview {{
                margin-top: 20px;
                flex: 1;
                display: flex;
                flex-direction: column;
            }}

            .data-preview-content {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                overflow-y: auto;
                flex: 1;
                min-height: 400px;
                max-height: 600px;
                font-size: 12px;
                line-height: 1.4;
                white-space: pre-wrap;
                word-wrap: break-word;
                font-family: 'Courier New', monospace;
            }}
        </style>
        """

        return html_content
    
    def get_qa_content(self):
        """获取问答阶段内容"""
        if not self.current_doc:
            return "<p>❌ 未选择文档</p>"
        
        # 加载问答结果
        qa_results = self.loader.load_qa_results(self.current_config)
        
        if not qa_results:
            return f"<p>❌ 配置 '{self.current_config}' 的问答结果不存在</p>"
        
        # 统计分析
        total_questions = len(qa_results)
        answered_questions = sum(1 for qa in qa_results if qa.get('value') is not None and str(qa.get('value', '')).strip() and qa.get('value', '') != 'N/A')
        
        # 按类型统计
        type_stats = {}
        for qa in qa_results:
            qtype = qa.get('kind', '未知')
            type_stats[qtype] = type_stats.get(qtype, 0) + 1
        
        # 创建统计HTML
        qa_detail_html = f"""
        <div class='qa-results'>
            <h3>🎯 问答结果统计</h3>
            <div class='stats-grid'>
                <div class='stat-item'>
                    <strong>问题总数:</strong> {total_questions}
                </div>
                <div class='stat-item'>
                    <strong>已回答:</strong> {answered_questions} ({round(answered_questions/total_questions*100, 1) if total_questions else 0}%)
                </div>
                <div class='stat-item'>
                    <strong>使用配置:</strong> {self.current_config}
                </div>
                <div class='stat-item'>
                    <strong>问题类型:</strong> {', '.join([f"{k}({v})" for k, v in type_stats.items()])}
                </div>
            </div>
            
            <h4>💬 详细问答结果 (前10个)</h4>
        """
        
        for i, qa in enumerate(qa_results[:10]):  # 只显示前10个
            question = qa.get('question_text', '无问题')
            value = qa.get('value')
            answer = str(value) if value is not None else '无答案'
            references = qa.get('references', [])
            kind = qa.get('kind', '未知')
            
            # 处理错误信息
            error_info = qa.get('error', '')
            if error_info:
                answer += f" (错误: {error_info[:100]}...)" if len(error_info) > 100 else f" (错误: {error_info})"
            
            qa_detail_html += f"""
            <div class='qa-detail-item'>
                <div class='qa-number'>Q{i+1}</div>
                <div class='qa-content'>
                    <div class='qa-question'>
                        <strong>问题 ({kind}):</strong> {question}
                    </div>
                    <div class='qa-answer'>
                        <strong>答案:</strong> {answer}
                    </div>
                    <div class='qa-citations'>
                        <strong>引用:</strong> {len(references)} 个引用
                        {' | '.join([f"页面 {ref.get('page_index', '?')}" for ref in references[:3]]) if references else '无引用'}
                    </div>
                </div>
            </div>
            """
        
        if len(qa_results) > 10:
            qa_detail_html += f"<p><em>... 还有 {len(qa_results) - 10} 个问答对</em></p>"
        
        qa_detail_html += """
        </div>
        
        <style>
            .qa-results {{ background: white; padding: 20px; border-radius: 8px; margin: 10px 0; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0; }}
            .stat-item {{ padding: 10px; background: #f0f8ff; border-radius: 6px; }}
            .qa-detail-item {{
                display: flex;
                gap: 15px;
                margin: 15px 0;
                padding: 15px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #fafafa;
            }}
            .qa-number {{
                width: 40px;
                height: 40px;
                background: #2196f3;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                flex-shrink: 0;
            }}
            .qa-content {{
                flex: 1;
            }}
            .qa-question {{
                margin-bottom: 10px;
                color: #1976d2;
            }}
            .qa-answer {{
                margin-bottom: 10px;
                color: #388e3c;
                line-height: 1.5;
            }}
            .qa-citations {{
                color: #666;
                font-size: 14px;
            }}
        </style>
        """
        
        return qa_detail_html
    
    def create_interface(self):
        """创建Gradio界面"""
        with gr.Blocks(
            title="RAG Challenge 复现结果可视化",
            theme=gr.themes.Soft(primary_hue="blue"),
            css="""
            .main-container { max-width: 1400px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; }
            .config-panel { background: #f0f8ff; padding: 10px; border-radius: 10px; margin-bottom: 15px; flex-shrink: 0; }
            .tab-content { min-height: 800px; max-height: 900px; overflow-y: auto; }
            .markdown-content { max-height: 600px; overflow-y: auto; }
            .content-row { flex: 1; display: flex; gap: 15px; min-height: 0; }
            .pdf-column { flex: 1; display: flex; flex-direction: column; min-height: 0; }
            .tabs-column { flex: 1; display: flex; flex-direction: column; min-height: 0; }
            .pdf-viewer-html { flex: 1 !important; height: 100% !important; }
            """
        ) as interface:
            
            with gr.Column(elem_classes="main-container"):
                with gr.Row():
                    gr.Markdown("# 🏆 RAG Challenge 复现结果可视化")
                
                # 配置面板
                with gr.Row(elem_classes="config-panel"):
                    with gr.Column(scale=2):
                        doc_dropdown = gr.Dropdown(
                            choices=self.available_docs,
                            value=self.current_doc,
                            label="📄 选择文档",
                            info="选择要查看的PDF报告"
                        )
                    
                    with gr.Column(scale=2):
                        config_dropdown = gr.Dropdown(
                            choices=self.available_configs,
                            value=self.current_config,
                            label="⚙️ 问答配置",
                            info="选择问答结果的配置版本"
                        )
                    
                    with gr.Column(scale=1):
                        refresh_btn = gr.Button("🔄 刷新", variant="primary")
                
                # 主要内容区域
                with gr.Row(elem_classes="content-row"):
                    # 左侧PDF预览
                    with gr.Column(scale=1, elem_classes="pdf-column"):
                        pdf_viewer = gr.HTML(
                            "<p>📄 PDF文档将在此显示...</p>",
                            label="PDF预览",
                            elem_classes="pdf-viewer-html"
                        )
                    
                    # 右侧标签页内容
                    with gr.Column(scale=1, elem_classes="tabs-column"):
                        with gr.Tabs():
                            with gr.Tab("🎯 问答结果"):
                                qa_content = gr.HTML(
                                    "<p>问答结果将在此显示...</p>",
                                    elem_classes="tab-content"
                                )

                            with gr.Tab("📄 PDF解析") as parsing_tab:
                                parsing_content = gr.HTML(
                                    "<p>点击该标签页后加载 PDF 解析结果...</p>",
                                    elem_classes="tab-content"
                                )

                            with gr.Tab("🔄 序列化") as serialization_tab:
                                serialization_content = gr.HTML(
                                    "<p>点击该标签页后加载序列化结果...</p>",
                                    elem_classes="tab-content"
                                )

                            with gr.Tab("💾 数据注入") as ingestion_tab:
                                ingestion_content = gr.HTML(
                                    "<p>点击该标签页后加载数据注入结果...</p>",
                                    elem_classes="tab-content"
                                )
                
                # 事件处理
                doc_dropdown.change(
                    fn=self.update_document,
                    inputs=[doc_dropdown],
                    outputs=[pdf_viewer, parsing_content, serialization_content, ingestion_content, qa_content]
                )
                
                config_dropdown.change(
                    fn=self.update_config,
                    inputs=[config_dropdown],
                    outputs=[qa_content]
                )

                parsing_tab.select(
                    fn=self.get_parsing_content,
                    outputs=[parsing_content]
                )

                serialization_tab.select(
                    fn=self.get_serialization_content,
                    outputs=[serialization_content]
                )

                ingestion_tab.select(
                    fn=self.get_ingestion_content,
                    outputs=[ingestion_content]
                )
                
                refresh_btn.click(
                    fn=self.refresh_all_content,
                    outputs=[pdf_viewer, parsing_content, serialization_content, ingestion_content, qa_content]
                )
                
                # 页面加载时初始化内容
                interface.load(
                    fn=self.refresh_all_content,
                    outputs=[pdf_viewer, parsing_content, serialization_content, ingestion_content, qa_content]
                )
        
        return interface


def main():
    """主函数"""
    # 检查数据路径
    current_dir = Path(__file__).parent
    data_path = current_dir / "../data/test_set"
    
    if not data_path.exists():
        print(f"❌ 数据目录不存在: {data_path}")
        print("请确保在正确的目录下运行，且数据已准备完毕")
        return
    
    print(f"✅ 数据目录: {data_path}")
    
    # 创建应用
    app = RAGVisualizationApp(str(data_path))
    
    if not app.available_docs:
        print("❌ 未找到可用的PDF文档")
        return
    
    print(f"✅ 找到 {len(app.available_docs)} 个文档: {app.available_docs}")
    print(f"✅ 找到 {len(app.available_configs)} 个配置: {app.available_configs}")
    
    # 创建并启动界面
    interface = app.create_interface()
    
    print("🚀 启动可视化界面...")
    print("📝 界面地址: http://127.0.0.1:7860")
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main() 