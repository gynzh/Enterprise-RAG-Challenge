import json
import gradio as gr
from typing import Any, Dict, List, Optional
import pandas as pd


class JSONViewer:
    """JSON数据可视化查看器"""
    
    @staticmethod
    def format_json_tree(data: Any, max_depth: int = 3, current_depth: int = 0) -> str:
        """
        将JSON数据格式化为树状结构的HTML
        
        Args:
            data: JSON数据
            max_depth: 最大显示深度
            current_depth: 当前深度
            
        Returns:
            HTML格式的树状结构字符串
        """
        if current_depth > max_depth:
            return f"<span class='json-truncated'>... (深度过深，已截断)</span>"
            
        if isinstance(data, dict):
            if not data:
                return "<span class='json-empty'>{}</span>"
                
            html = "<ul class='json-dict'>"
            for key, value in list(data.items())[:20]:  # 限制显示前20个键
                value_html = JSONViewer.format_json_tree(value, max_depth, current_depth + 1)
                html += f"<li><strong class='json-key'>{key}:</strong> {value_html}</li>"
            
            if len(data) > 20:
                html += f"<li><span class='json-more'>... 还有 {len(data) - 20} 个字段</span></li>"
            html += "</ul>"
            return html
            
        elif isinstance(data, list):
            if not data:
                return "<span class='json-empty'>[]</span>"
                
            html = f"<span class='json-array-info'>数组 ({len(data)} 项)</span><ul class='json-array'>"
            for i, item in enumerate(data[:10]):  # 只显示前10项
                item_html = JSONViewer.format_json_tree(item, max_depth, current_depth + 1)
                html += f"<li><span class='json-index'>[{i}]:</span> {item_html}</li>"
                
            if len(data) > 10:
                html += f"<li><span class='json-more'>... 还有 {len(data) - 10} 项</span></li>"
            html += "</ul>"
            return html
            
        elif isinstance(data, str):
            if len(data) > 100:
                preview = data[:100] + "..."
                return f"<span class='json-string'>\"{preview}\" <small>({len(data)} 字符)</small></span>"
            return f"<span class='json-string'>\"{data}\"</span>"
            
        elif isinstance(data, (int, float)):
            return f"<span class='json-number'>{data}</span>"
            
        elif isinstance(data, bool):
            return f"<span class='json-boolean'>{str(data).lower()}</span>"
            
        elif data is None:
            return "<span class='json-null'>null</span>"
            
        else:
            return f"<span class='json-unknown'>{str(data)}</span>"
    
    @staticmethod
    def create_summary_table(data: Dict[str, Any]) -> str:
        """
        创建JSON数据的摘要表格
        
        Args:
            data: JSON数据
            
        Returns:
            HTML格式的摘要表格
        """
        def count_items(obj, item_type=None):
            """递归统计各种类型的数据项"""
            counts = {
                'objects': 0,
                'arrays': 0, 
                'strings': 0,
                'numbers': 0,
                'booleans': 0,
                'nulls': 0,
                'total_keys': 0
            }
            
            if isinstance(obj, dict):
                counts['objects'] += 1
                counts['total_keys'] += len(obj)
                for value in obj.values():
                    sub_counts = count_items(value)
                    for key in counts:
                        counts[key] += sub_counts[key]
                        
            elif isinstance(obj, list):
                counts['arrays'] += 1
                for item in obj:
                    sub_counts = count_items(item)
                    for key in counts:
                        counts[key] += sub_counts[key]
                        
            elif isinstance(obj, str):
                counts['strings'] += 1
            elif isinstance(obj, (int, float)):
                counts['numbers'] += 1
            elif isinstance(obj, bool):
                counts['booleans'] += 1
            elif obj is None:
                counts['nulls'] += 1
                
            return counts
        
        stats = count_items(data)
        
        html = """
        <table class='summary-table'>
            <tr><th>数据类型</th><th>数量</th></tr>
            <tr><td>总对象数</td><td>{objects}</td></tr>
            <tr><td>总数组数</td><td>{arrays}</td></tr>
            <tr><td>总键数</td><td>{total_keys}</td></tr>
            <tr><td>字符串</td><td>{strings}</td></tr>
            <tr><td>数字</td><td>{numbers}</td></tr>
            <tr><td>布尔值</td><td>{booleans}</td></tr>
            <tr><td>空值</td><td>{nulls}</td></tr>
        </table>
        """.format(**stats)
        
        return html
    
    @staticmethod
    def create_tables_overview(tables_data: List[Dict[str, Any]]) -> str:
        """
        创建表格数据概览
        
        Args:
            tables_data: 表格数据列表
            
        Returns:
            HTML格式的表格概览
        """
        if not tables_data:
            return "<p>❌ 未找到表格数据</p>"
            
        html = f"<h4>📊 表格数据概览 (共 {len(tables_data)} 个表格)</h4>"
        
        # 创建表格统计
        df_data = []
        for i, table in enumerate(tables_data):
            row_data = {
                "表格ID": i + 1,
                "页码": table.get("page", "未知"),
                "行数": table.get("#-rows", 0),
                "列数": table.get("#-cols", 0),
                "有Markdown": "✅" if "markdown" in table else "❌",
                "有HTML": "✅" if "html" in table else "❌"
            }
            df_data.append(row_data)
            
        df = pd.DataFrame(df_data)
        html += df.to_html(classes='tables-overview', index=False, escape=False)
        
        return html
    
    @staticmethod
    def create_pages_overview(pages_data: List[Dict[str, Any]]) -> str:
        """
        创建页面数据概览
        
        Args:
            pages_data: 页面数据列表
            
        Returns:
            HTML格式的页面概览
        """
        if not pages_data:
            return "<p>❌ 未找到页面数据</p>"
            
        html = f"<h4>📄 页面数据概览 (共 {len(pages_data)} 页)</h4>"
        
        # 页面统计
        df_data = []
        for i, page in enumerate(pages_data):
            text_length = len(page.get("text", ""))
            row_data = {
                "页码": i + 1,
                "文本长度": text_length,
                "文本预览": page.get("text", "")[:100] + "..." if text_length > 100 else page.get("text", ""),
                "有表格": "✅" if page.get("tables") else "❌",
                "表格数量": len(page.get("tables", []))
            }
            df_data.append(row_data)
            
        df = pd.DataFrame(df_data)
        html += df.to_html(classes='pages-overview', index=False, escape=False)
        
        return html
    
    @staticmethod
    def create_json_viewer_interface(data: Dict[str, Any], title: str = "JSON数据查看器") -> gr.HTML:
        """
        创建JSON查看器界面
        
        Args:
            data: 要显示的JSON数据
            title: 界面标题
            
        Returns:
            Gradio HTML组件
        """
        if not data:
            return gr.HTML("<p>❌ 暂无数据</p>")
            
        # 创建完整的HTML内容
        html_content = f"""
        <div class='json-viewer'>
            <h3>{title}</h3>
            
            <!-- 数据摘要 -->
            <div class='json-summary'>
                <h4>📊 数据摘要</h4>
                {JSONViewer.create_summary_table(data)}
            </div>
            
            <!-- 特殊内容展示 -->
        """
        
        # 如果有表格数据，单独展示
        if "tables" in data and isinstance(data["tables"], list):
            html_content += f"""
            <div class='tables-section'>
                {JSONViewer.create_tables_overview(data["tables"])}
            </div>
            """
        
        # 如果有页面数据，单独展示  
        if "content" in data and "pages" in data["content"]:
            html_content += f"""
            <div class='pages-section'>
                {JSONViewer.create_pages_overview(data["content"]["pages"])}
            </div>
            """
            
        # JSON树状结构
        html_content += f"""
            <!-- JSON树状结构 -->
            <div class='json-tree-section'>
                <h4>🌳 完整数据结构</h4>
                <div class='json-tree'>
                    {JSONViewer.format_json_tree(data)}
                </div>
            </div>
        </div>
        
        <style>
            .json-viewer {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
            }}
            
            .json-tree {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 16px;
                max-height: 600px;
                overflow-y: auto;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }}
            
            .json-dict, .json-array {{
                margin: 0;
                padding-left: 20px;
                list-style: none;
            }}
            
            .json-key {{
                color: #0066cc;
                font-weight: bold;
            }}
            
            .json-string {{
                color: #008000;
            }}
            
            .json-number {{
                color: #ff6600;
                font-weight: bold;
            }}
            
            .json-boolean {{
                color: #cc0066;
                font-weight: bold;
            }}
            
            .json-null {{
                color: #666;
                font-style: italic;
            }}
            
            .json-array-info {{
                color: #9932cc;
                font-weight: bold;
            }}
            
            .json-index {{
                color: #666;
            }}
            
            .json-more {{
                color: #999;
                font-style: italic;
            }}
            
            .json-empty {{
                color: #999;
                font-style: italic;
            }}
            
            .json-truncated {{
                color: #ff6666;
                font-style: italic;
            }}
            
            .summary-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            
            .summary-table th, .summary-table td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            
            .summary-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            
            .tables-overview, .pages-overview {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
                font-size: 12px;
            }}
            
            .tables-overview th, .tables-overview td,
            .pages-overview th, .pages-overview td {{
                border: 1px solid #ddd;
                padding: 6px;
                text-align: left;
            }}
            
            .tables-overview th, .pages-overview th {{
                background-color: #e3f2fd;
                font-weight: bold;
            }}
            
            .json-summary, .tables-section, .pages-section {{
                margin: 20px 0;
                padding: 15px;
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }}
        </style>
        """
        
        return gr.HTML(html_content) 