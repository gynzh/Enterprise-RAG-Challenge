import gradio as gr
import base64
from pathlib import Path
from typing import Optional, Tuple


class PDFViewer:
    """PDF文档在线查看器"""
    
    @staticmethod
    def load_pdf_base64(pdf_path: str) -> Optional[str]:
        """
        将PDF文件转换为base64编码
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            base64编码的PDF数据，如果文件不存在返回None
        """
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            return None
            
        try:
            with open(pdf_file, 'rb') as f:
                pdf_data = f.read()
            
            # 转换为base64
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
            return pdf_base64
            
        except Exception as e:
            print(f"加载PDF文件失败: {e}")
            return None
    
    @staticmethod
    def create_pdf_viewer(pdf_path: str, doc_id: str) -> gr.HTML:
        """
        创建PDF查看器界面
        
        Args:
            pdf_path: PDF文件路径
            doc_id: 文档ID
            
        Returns:
            包含PDF查看器的Gradio HTML组件
        """
        pdf_base64 = PDFViewer.load_pdf_base64(pdf_path)
        
        if not pdf_base64:
            return gr.HTML(f"""
                <div class='pdf-error'>
                    <h3>❌ PDF文件加载失败</h3>
                    <p>文件路径: {pdf_path}</p>
                    <p>文档ID: {doc_id}</p>
                    <p>请检查文件是否存在或路径是否正确。</p>
                </div>
                
                <style>
                    .pdf-error {{
                        text-align: center;
                        padding: 40px;
                        border: 2px dashed #ff6b6b;
                        border-radius: 10px;
                        background-color: #ffe0e0;
                        color: #cc0000;
                    }}
                </style>
            """)
        
        # 获取文件信息
        pdf_file = Path(pdf_path)
        file_size_mb = round(pdf_file.stat().st_size / (1024*1024), 2)
        
        html_content = f"""
        <div class='pdf-viewer-container'>
            <div class='pdf-header'>
                <h3>📄 PDF文档预览</h3>
                <div class='pdf-info'>
                    <span class='doc-id'>文档ID: {doc_id}</span>
                    <span class='file-size'>文件大小: {file_size_mb} MB</span>
                </div>
            </div>
            
            <div class='pdf-controls'>
                <button onclick='zoomIn()' class='control-btn'>🔍 放大</button>
                <button onclick='zoomOut()' class='control-btn'>🔍 缩小</button>
                <button onclick='resetZoom()' class='control-btn'>↻ 重置</button>
                <button onclick='toggleFullscreen()' class='control-btn'>⛶ 全屏</button>
                <span class='zoom-info'>缩放: <span id='zoomLevel'>100%</span></span>
            </div>
            
            <div class='pdf-embed-container' id='pdfContainer'>
                <embed 
                    id='pdfEmbed'
                    src='data:application/pdf;base64,{pdf_base64}' 
                    type='application/pdf' 
                    width='100%' 
                    height='100%'
                    style='border: 1px solid #ddd; border-radius: 8px;'
                />
            </div>
            
            <div class='pdf-fallback'>
                <p>如果PDF无法显示，请尝试:</p>
                <ul>
                    <li><a href='data:application/pdf;base64,{pdf_base64}' download='{doc_id}.pdf' class='download-link'>📥 下载PDF文件</a></li>
                    <li>使用Chrome或Firefox浏览器</li>
                    <li>启用浏览器的PDF查看器</li>
                </ul>
            </div>
        </div>
        
        <style>
            .pdf-viewer-container {{
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 12px;
                background: #ffffff;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
                height: calc(100vh - 130px);
                overflow: hidden;
            }}
            
            .pdf-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
                padding-bottom: 6px;
                border-bottom: 1px solid #e0e0e0;
                flex-shrink: 0;
            }}
            
            .pdf-header h3 {{
                margin: 0;
                color: #333;
            }}
            
            .pdf-info {{
                display: flex;
                gap: 20px;
                font-size: 14px;
                color: #666;
            }}
            
            .doc-id {{
                background: #e3f2fd;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: monospace;
            }}
            
            .file-size {{
                background: #f3e5f5;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            
            .pdf-controls {{
                display: flex;
                gap: 10px;
                align-items: center;
                margin-bottom: 10px;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 6px;
                flex-shrink: 0;
            }}
            
            .control-btn {{
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            }}
            
            .control-btn:hover {{
                background: #0056b3;
            }}
            
            .zoom-info {{
                margin-left: auto;
                font-weight: bold;
                color: #666;
            }}
            
            .pdf-embed-container {{
                position: relative;
                flex: 1;
                min-height: 500px;
                height: 100%;
            }}
            
            .pdf-fallback {{
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 6px;
                padding: 10px;
                margin-top: 10px;
                flex-shrink: 0;
                font-size: 12px;
            }}
            
            .pdf-fallback p {{
                margin: 0 0 10px 0;
                font-weight: bold;
                color: #856404;
            }}
            
            .pdf-fallback ul {{
                margin: 0;
                padding-left: 20px;
                color: #856404;
            }}
            
            .download-link {{
                color: #007bff;
                text-decoration: none;
                font-weight: bold;
            }}
            
            .download-link:hover {{
                text-decoration: underline;
            }}
            
            .fullscreen {{
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                z-index: 9999 !important;
                background: white !important;
            }}
        </style>
        
        <script>
            let currentZoom = 1.0;
            
            function zoomIn() {{
                currentZoom += 0.2;
                updateZoom();
            }}
            
            function zoomOut() {{
                if (currentZoom > 0.4) {{
                    currentZoom -= 0.2;
                    updateZoom();
                }}
            }}
            
            function resetZoom() {{
                currentZoom = 1.0;
                updateZoom();
            }}
            
            function updateZoom() {{
                const embed = document.getElementById('pdfEmbed');
                if (embed) {{
                    embed.style.transform = `scale(${{currentZoom}})`;
                    embed.style.transformOrigin = 'top left';
                    
                    const container = document.getElementById('pdfContainer');
                    container.style.height = `${{600 * currentZoom}}px`;
                    
                    const zoomLevel = document.getElementById('zoomLevel');
                    if (zoomLevel) {{
                        zoomLevel.textContent = `${{Math.round(currentZoom * 100)}}%`;
                    }}
                }}
            }}
            
            function toggleFullscreen() {{
                const container = document.getElementById('pdfContainer');
                if (container) {{
                    if (container.classList.contains('fullscreen')) {{
                        container.classList.remove('fullscreen');
                        resetZoom();
                    }} else {{
                        container.classList.add('fullscreen');
                        currentZoom = 1.0;
                        updateZoom();
                    }}
                }}
            }}
            
            // 添加ESC键退出全屏
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') {{
                    const container = document.getElementById('pdfContainer');
                    if (container && container.classList.contains('fullscreen')) {{
                        container.classList.remove('fullscreen');
                        resetZoom();
                    }}
                }}
            }});
        </script>
        """
        
        return gr.HTML(html_content)
    
    @staticmethod
    def create_simple_pdf_display(pdf_path: str) -> gr.File:
        """
        创建简单的PDF文件显示组件（备用方案）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Gradio File组件
        """
        pdf_file = Path(pdf_path)
        
        if pdf_file.exists():
            return gr.File(value=str(pdf_file), label=f"PDF文档: {pdf_file.name}")
        else:
            return gr.File(label="PDF文件不存在")
    
    @staticmethod
    def get_pdf_info(pdf_path: str) -> dict:
        """
        获取PDF文件信息
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            包含PDF信息的字典
        """
        pdf_file = Path(pdf_path)
        
        info = {
            "exists": pdf_file.exists(),
            "file_name": pdf_file.name,
            "file_path": str(pdf_file),
            "size_bytes": 0,
            "size_mb": 0
        }
        
        if pdf_file.exists():
            size_bytes = pdf_file.stat().st_size
            info.update({
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024*1024), 2)
            })
            
        return info 