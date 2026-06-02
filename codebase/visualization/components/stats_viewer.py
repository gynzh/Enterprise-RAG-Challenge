import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Any, Optional
import numpy as np


class StatsViewer:
    """统计数据可视化组件"""
    
    @staticmethod
    def create_parsing_stats(doc_info: Dict[str, Any], parsing_stats: Dict[str, Any]) -> gr.HTML:
        """
        创建PDF解析阶段的统计展示
        
        Args:
            doc_info: 文档基本信息
            parsing_stats: 解析统计信息
            
        Returns:
            统计信息的HTML组件
        """
        html_content = f"""
        <div class='stats-container'>
            <h3>📊 PDF解析阶段统计</h3>
            
            <div class='stats-grid'>
                <div class='stat-card'>
                    <div class='stat-icon'>📄</div>
                    <div class='stat-content'>
                        <div class='stat-title'>文档基本信息</div>
                        <div class='stat-value'>{parsing_stats.get('company_name', '未知公司')}</div>
                        <div class='stat-detail'>页数: {parsing_stats.get('pages_amount', 0)} 页</div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>📊</div>
                    <div class='stat-content'>
                        <div class='stat-title'>表格统计</div>
                        <div class='stat-value'>{parsing_stats.get('tables_count', 0)} 个</div>
                        <div class='stat-detail'>
                            Markdown: {parsing_stats.get('tables_with_markdown', 0)} / {parsing_stats.get('tables_count', 0)}
                        </div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>📝</div>
                    <div class='stat-content'>
                        <div class='stat-title'>文本统计</div>
                        <div class='stat-value'>{parsing_stats.get('total_text_length', 0):,} 字符</div>
                        <div class='stat-detail'>
                            平均每页: {int(parsing_stats.get('avg_text_per_page', 0))} 字符
                        </div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>💾</div>
                    <div class='stat-content'>
                        <div class='stat-title'>文件大小</div>
                        <div class='stat-value'>{doc_info.get('pdf_size_mb', 0)} MB</div>
                        <div class='stat-detail'>
                            JSON: {round(doc_info.get('parsing_size', 0) / (1024*1024), 2) if doc_info.get('parsing_size') else 0} MB
                        </div>
                    </div>
                </div>
            </div>
            
            <div class='processing-status'>
                <h4>🔄 处理状态检查</h4>
                <div class='status-grid'>
                    <div class='status-item'>
                        <span class='status-label'>PDF解析:</span>
                        <span class='status-{'success' if doc_info.get('parsing_exists') else 'error'}'>
                            {'✅ 完成' if doc_info.get('parsing_exists') else '❌ 未完成'}
                        </span>
                    </div>
                    <div class='status-item'>
                        <span class='status-label'>报告合并:</span>
                        <span class='status-{'success' if doc_info.get('merged_exists') else 'error'}'>
                            {'✅ 完成' if doc_info.get('merged_exists') else '❌ 未完成'}
                        </span>
                    </div>
                    <div class='status-item'>
                        <span class='status-label'>Markdown转换:</span>
                        <span class='status-{'success' if doc_info.get('markdown_exists') else 'error'}'>
                            {'✅ 完成' if doc_info.get('markdown_exists') else '❌ 未完成'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .stats-container {{
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                margin: 10px 0;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .stat-icon {{
                font-size: 24px;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #e3f2fd;
                border-radius: 50%;
            }}
            
            .stat-content {{
                flex: 1;
            }}
            
            .stat-title {{
                font-size: 12px;
                color: #666;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .stat-value {{
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-bottom: 2px;
            }}
            
            .stat-detail {{
                font-size: 12px;
                color: #888;
            }}
            
            .processing-status {{
                background: white;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
            }}
            
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
                margin-top: 10px;
            }}
            
            .status-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: #f8f9fa;
                border-radius: 6px;
            }}
            
            .status-label {{
                font-weight: 500;
                color: #555;
            }}
            
            .status-success {{
                color: #28a745;
                font-weight: bold;
            }}
            
            .status-error {{
                color: #dc3545;
                font-weight: bold;
            }}
        </style>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_vectorization_stats(vector_stats: Dict[str, Any]) -> gr.HTML:
        """
        创建向量化阶段的统计展示
        
        Args:
            vector_stats: 向量化统计信息
            
        Returns:
            统计信息的HTML组件
        """
        html_content = f"""
        <div class='stats-container'>
            <h3>🔧 数据注入阶段统计</h3>
            
            <div class='stats-grid'>
                <div class='stat-card'>
                    <div class='stat-icon'>🧩</div>
                    <div class='stat-content'>
                        <div class='stat-title'>切块统计</div>
                        <div class='stat-value'>{vector_stats.get('total_chunks', 0)} 个</div>
                        <div class='stat-detail'>
                            平均长度: {int(vector_stats.get('avg_chunk_length', 0))} tokens
                        </div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>📄</div>
                    <div class='stat-content'>
                        <div class='stat-title'>页面覆盖</div>
                        <div class='stat-value'>{vector_stats.get('pages_with_chunks', 0)} 页</div>
                        <div class='stat-detail'>
                            每页平均: {vector_stats.get('chunks_per_page', 0)} 切块
                        </div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>💾</div>
                    <div class='stat-content'>
                        <div class='stat-title'>向量数据库</div>
                        <div class='stat-value'>{vector_stats.get('faiss_size_mb', 0)} MB</div>
                        <div class='stat-detail'>
                            {'✅ FAISS已创建' if vector_stats.get('faiss_exists') else '❌ FAISS未创建'}
                        </div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>🔢</div>
                    <div class='stat-content'>
                        <div class='stat-title'>Token统计</div>
                        <div class='stat-value'>{vector_stats.get('total_tokens', 0):,}</div>
                        <div class='stat-detail'>总Token数量</div>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .stats-container {{
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                margin: 10px 0;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .stat-icon {{
                font-size: 24px;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #e8f5e8;
                border-radius: 50%;
            }}
            
            .stat-content {{
                flex: 1;
            }}
            
            .stat-title {{
                font-size: 12px;
                color: #666;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .stat-value {{
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-bottom: 2px;
            }}
            
            .stat-detail {{
                font-size: 12px;
                color: #888;
            }}
        </style>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_qa_results_stats(qa_results: List[Dict[str, Any]]) -> gr.HTML:
        """
        创建问答结果统计展示
        
        Args:
            qa_results: 问答结果列表
            
        Returns:
            统计信息的HTML组件
        """
        if not qa_results:
            return gr.HTML("<p>❌ 暂无问答结果数据</p>")
        
        # 统计分析
        total_questions = len(qa_results)
        answered_questions = sum(1 for qa in qa_results if qa.get('value') is not None and str(qa.get('value', '')).strip() and qa.get('value', '') != 'N/A')
        
        # 答案长度统计
        answer_lengths = [len(str(qa.get('value', ''))) for qa in qa_results if qa.get('value') is not None and qa.get('value') != 'N/A']
        avg_answer_length = sum(answer_lengths) / len(answer_lengths) if answer_lengths else 0
        
        # 引用统计
        citation_counts = []
        for qa in qa_results:
            references = qa.get('references', [])
            citation_counts.append(len(references) if references else 0)
        
        avg_citations = sum(citation_counts) / len(citation_counts) if citation_counts else 0
        
        html_content = f"""
        <div class='stats-container'>
            <h3>❓ 问答结果统计</h3>
            
            <div class='stats-grid'>
                <div class='stat-card'>
                    <div class='stat-icon'>❓</div>
                    <div class='stat-content'>
                        <div class='stat-title'>问题总数</div>
                        <div class='stat-value'>{total_questions}</div>
                        <div class='stat-detail'>
                            已回答: {answered_questions} ({round(answered_questions/total_questions*100, 1) if total_questions else 0}%)
                        </div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>💬</div>
                    <div class='stat-content'>
                        <div class='stat-title'>答案长度</div>
                        <div class='stat-value'>{int(avg_answer_length)} 字符</div>
                        <div class='stat-detail'>平均长度</div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>🔗</div>
                    <div class='stat-content'>
                        <div class='stat-title'>引用统计</div>
                        <div class='stat-value'>{round(avg_citations, 1)} 个</div>
                        <div class='stat-detail'>平均引用数</div>
                    </div>
                </div>
                
                <div class='stat-card'>
                    <div class='stat-icon'>✅</div>
                    <div class='stat-content'>
                        <div class='stat-title'>完成率</div>
                        <div class='stat-value'>{round(answered_questions/total_questions*100, 1) if total_questions else 0}%</div>
                        <div class='stat-detail'>回答完整性</div>
                    </div>
                </div>
            </div>
            
            <div class='qa-sample'>
                <h4>📝 问答示例 (前3个)</h4>
        """
        
        # 显示前3个问答示例
        for i, qa in enumerate(qa_results[:3]):
            question = qa.get('question_text', '无问题')
            value = qa.get('value')
            answer = str(value) if value is not None else '无答案'
            references = qa.get('references', [])
            kind = qa.get('kind', '未知类型')
            
            # 截断过长的答案
            if len(answer) > 200:
                answer_preview = answer[:200] + "..."
            else:
                answer_preview = answer
                
            html_content += f"""
            <div class='qa-item'>
                <div class='qa-question'>
                    <strong>Q{i+1} ({kind}):</strong> {question}
                </div>
                <div class='qa-answer'>
                    <strong>A:</strong> {answer_preview}
                </div>
                <div class='qa-citations'>
                    <strong>引用:</strong> {len(references)} 个引用
                </div>
            </div>
            """
        
        html_content += """
            </div>
        </div>
        
        <style>
            .stats-container {
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                margin: 10px 0;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            
            .stat-card {
                background: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 15px;
            }
            
            .stat-icon {
                font-size: 24px;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #fff3e0;
                border-radius: 50%;
            }
            
            .stat-content {
                flex: 1;
            }
            
            .stat-title {
                font-size: 12px;
                color: #666;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .stat-value {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-bottom: 2px;
            }
            
            .stat-detail {
                font-size: 12px;
                color: #888;
            }
            
            .qa-sample {
                background: white;
                border-radius: 8px;
                padding: 15px;
                margin-top: 20px;
            }
            
            .qa-item {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 12px;
                margin: 10px 0;
                background: #fafafa;
            }
            
            .qa-question {
                color: #1976d2;
                margin-bottom: 8px;
                font-weight: 500;
            }
            
            .qa-answer {
                color: #388e3c;
                margin-bottom: 8px;
                line-height: 1.4;
            }
            
            .qa-citations {
                color: #666;
                font-size: 12px;
            }
        </style>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_chunk_distribution_chart(chunked_data: Dict[str, Any]) -> Optional[gr.Plot]:
        """
        创建切块分布图表
        
        Args:
            chunked_data: 切块数据
            
        Returns:
            Plotly图表组件
        """
        if not chunked_data or "content" not in chunked_data:
            return None
            
        chunks = chunked_data["content"].get("chunks", [])
        if not chunks:
            return None
            
        # 按页面统计切块数量
        page_counts = {}
        token_counts = {}
        
        for chunk in chunks:
            page = chunk.get("page", 0)
            tokens = chunk.get("length_tokens", 0)
            
            if page not in page_counts:
                page_counts[page] = 0
                token_counts[page] = 0
            
            page_counts[page] += 1
            token_counts[page] += tokens
        
        # 创建DataFrame
        df = pd.DataFrame({
            'Page': list(page_counts.keys()),
            'Chunks': list(page_counts.values()),
            'Tokens': list(token_counts.values())
        })
        
        # 创建图表
        fig = go.Figure()
        
        # 添加切块数量柱状图
        fig.add_trace(go.Bar(
            x=df['Page'],
            y=df['Chunks'],
            name='切块数量',
            marker_color='lightblue',
            yaxis='y'
        ))
        
        # 添加Token数量折线图
        fig.add_trace(go.Scatter(
            x=df['Page'],
            y=df['Tokens'],
            mode='lines+markers',
            name='Token数量',
            line=dict(color='red'),
            yaxis='y2'
        ))
        
        # 设置布局
        fig.update_layout(
            title='切块分布 - 按页面统计',
            xaxis_title='页码',
            yaxis=dict(title='切块数量', side='left'),
            yaxis2=dict(title='Token数量', side='right', overlaying='y'),
            legend=dict(x=0, y=1),
            height=400
        )
        
        return gr.Plot(value=fig) 