import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class RAGResultsLoader:
    """RAG处理结果数据加载器"""
    
    def __init__(self, base_path: str):
        """
        初始化数据加载器
        
        Args:
            base_path: 数据根目录路径，通常是 data/test_set
        """
        self.base_path = Path(base_path)
        self.pdf_reports_dir = self.base_path / "pdf_reports"
        self.debug_data_dir = self.base_path / "debug_data"
        self.databases_dir = self.base_path / "databases"
        
    def get_available_documents(self) -> List[str]:
        """
        获取所有可用的文档ID列表
        
        Returns:
            文档ID列表（不包含.pdf扩展名）
        """
        if not self.pdf_reports_dir.exists():
            return []
            
        pdf_files = list(self.pdf_reports_dir.glob("*.pdf"))
        return [f.stem for f in pdf_files]
    
    def get_document_info(self, doc_id: str) -> Dict[str, Any]:
        """
        获取文档基本信息
        
        Args:
            doc_id: 文档ID
            
        Returns:
            包含文档基本信息的字典
        """
        pdf_path = self.pdf_reports_dir / f"{doc_id}.pdf"
        
        info = {
            "document_id": doc_id,
            "pdf_exists": pdf_path.exists(),
            "pdf_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
            "pdf_size_mb": round(pdf_path.stat().st_size / (1024*1024), 2) if pdf_path.exists() else 0
        }
        
        # 检查各阶段处理结果是否存在
        stages = {
            "parsing": self.debug_data_dir / "01_parsed_reports" / f"{doc_id}.json",
            "merged": self.debug_data_dir / "02_merged_reports" / f"{doc_id}.json", 
            "markdown": self.debug_data_dir / "03_reports_markdown" / f"{doc_id}.md",
            "chunked": self.databases_dir / "chunked_reports" / f"{doc_id}.json",
            "vector_db": self.databases_dir / "vector_dbs" / f"{doc_id}.faiss"
        }
        
        for stage, path in stages.items():
            info[f"{stage}_exists"] = path.exists()
            if path.exists() and path.suffix == ".json":
                info[f"{stage}_size"] = path.stat().st_size
                
        return info
    
    def load_parsing_results(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        加载PDF解析结果
        
        Args:
            doc_id: 文档ID
            
        Returns:
            解析结果JSON数据，如果文件不存在返回None
        """
        json_path = self.debug_data_dir / "01_parsed_reports" / f"{doc_id}.json"
        
        if not json_path.exists():
            return None
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"加载解析结果失败: {e}")
            return None
    
    def load_merged_results(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        加载合并后的报告结果
        
        Args:
            doc_id: 文档ID
            
        Returns:
            合并结果JSON数据
        """
        json_path = self.debug_data_dir / "02_merged_reports" / f"{doc_id}.json"
        
        if not json_path.exists():
            return None
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"加载合并结果失败: {e}")
            return None
    
    def load_markdown_content(self, doc_id: str) -> Optional[str]:
        """
        加载Markdown格式的报告内容
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Markdown内容字符串
        """
        md_path = self.debug_data_dir / "03_reports_markdown" / f"{doc_id}.md"
        
        if not md_path.exists():
            return None
            
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"加载Markdown内容失败: {e}")
            return None
    
    def load_chunked_results(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        加载切块处理结果
        
        Args:
            doc_id: 文档ID
            
        Returns:
            切块结果JSON数据
        """
        json_path = self.databases_dir / "chunked_reports" / f"{doc_id}.json"
        
        if not json_path.exists():
            return None
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"加载切块结果失败: {e}")
            return None
    
    def get_vectorization_stats(self, doc_id: str) -> Dict[str, Any]:
        """
        获取向量化统计信息

        Args:
            doc_id: 文档ID

        Returns:
            向量化统计信息字典
        """
        faiss_path = self.databases_dir / "vector_dbs" / f"{doc_id}.faiss"
        faiss_exists = faiss_path.exists()
        faiss_size = faiss_path.stat().st_size if faiss_exists else 0

        chunked_data = self.load_chunked_results(doc_id)
        chunks = (
            chunked_data.get("content", {}).get("chunks", [])
            if chunked_data
            else []
        )

        total_chunks = len(chunks)
        total_tokens = sum(chunk.get("length_tokens", 0) for chunk in chunks)
        pages = {chunk.get("page", 0) for chunk in chunks}

        return {
            "document_id": doc_id,

            "faiss_exists": faiss_exists,
            "faiss_size": faiss_size,
            "faiss_size_mb": round(faiss_size / (1024 * 1024), 2),

            "total_chunks": total_chunks,
            "total_tokens": total_tokens,
            "avg_chunk_length": round(total_tokens / total_chunks, 2)
            if total_chunks
            else 0,

            "pages_with_chunks": len(pages),
            "chunks_per_page": round(total_chunks / len(pages), 2)
            if pages
            else 0,
        }
    
    def load_qa_results(self, config: str = "gemini_thinking_fc") -> Optional[List[Dict[str, Any]]]:
        """
        加载问答结果
        
        Args:
            config: 配置名称，用于确定答案文件名
            
        Returns:
            问答结果列表
        """
        # 尝试不同的答案文件名格式，优先加载debug版本
        possible_files = [
            f"answers_{config}_debug.json",  # 优先debug版本
            f"answers_{config}.json",
            "answers_gemini_thinking_fc_debug.json",
            "answers_base_debug.json", 
            "answers_gemini_thinking_fc.json",
            "answers_base.json"
        ]
        
        for filename in possible_files:
            answers_path = self.base_path / filename
            if answers_path.exists():
                try:
                    with open(answers_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # 处理不同格式的数据结构
                    if isinstance(data, dict):
                        if "questions" in data:  # debug版本使用questions
                            return data["questions"]
                        elif "answers" in data:  # 普通版本使用answers
                            return data["answers"]
                        else:
                            return data
                    else:
                        return data
                except Exception as e:
                    print(f"加载问答结果失败 {filename}: {e}")
                    continue
                    
        return None
    
    def get_available_configs(self) -> List[str]:
        """
        获取所有可用的配置列表

        Returns:
            配置名称列表
        """
        configs = []

        # 扫描答案文件
        for file_path in self.base_path.glob("answers_*.json"):
            # 从文件名提取配置名
            filename = file_path.stem
            if filename.startswith("answers_"):
                config_name = filename[8:]  # 移除 "answers_" 前缀
                if filename.endswith("_debug"):
                    config_name = config_name[:-6]  # 移除 "_debug" 后缀
                if config_name and config_name not in configs:
                    configs.append(config_name)

        return configs if configs else ["gemini_thinking_fc"]
    
    def get_parsing_statistics(self, doc_id: str) -> Dict[str, Any]:
        """
        获取解析阶段的统计信息
        
        Args:
            doc_id: 文档ID
            
        Returns:
            解析统计信息
        """
        stats = {}
        
        parsing_data = self.load_parsing_results(doc_id)
        if not parsing_data:
            return stats
            
        # 基本信息
        metainfo = parsing_data.get("metainfo", {})
        stats["company_name"] = metainfo.get("company_name", "Unknown")
        stats["pages_amount"] = metainfo.get("pages_amount", 0)
        stats["document_id"] = metainfo.get("sha1_name", doc_id)
        
        # 内容统计
        content = parsing_data.get("content", {})
        
        # 处理content可能是字典或列表的情况
        if isinstance(content, dict):
            pages = content.get("pages", [])
        elif isinstance(content, list):
            pages = content  # content本身就是pages列表
        else:
            pages = []
            
        stats["actual_pages"] = len(pages)
        
        # 表格统计
        tables = parsing_data.get("tables", [])
        stats["tables_count"] = len(tables)
        
        if tables:
            stats["tables_with_markdown"] = sum(1 for table in tables if "markdown" in table)
            stats["avg_table_rows"] = sum(table.get("#-rows", 0) for table in tables) / len(tables)
            stats["avg_table_cols"] = sum(table.get("#-cols", 0) for table in tables) / len(tables)
            
        # 页面内容统计
        if pages:
            total_text_length = 0
            for page in pages:
                if isinstance(page, dict):
                    total_text_length += len(page.get("text", ""))
                elif isinstance(page, str):
                    total_text_length += len(page)
            
            stats["total_text_length"] = total_text_length
            stats["avg_text_per_page"] = total_text_length / len(pages) if len(pages) > 0 else 0
            
        return stats 