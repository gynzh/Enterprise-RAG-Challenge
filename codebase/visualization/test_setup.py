#!/usr/bin/env python3
"""
可视化系统环境和数据测试脚本
"""

import sys
import os
from pathlib import Path

def test_imports():
    """测试必要的导入"""
    print("🔍 测试Python包导入...")
    
    try:
        import gradio as gr
        print("✅ Gradio:", gr.__version__)
    except ImportError:
        print("❌ Gradio 未安装")
        return False
    
    try:
        import pandas as pd
        print("✅ Pandas:", pd.__version__)
    except ImportError:
        print("❌ Pandas 未安装")
        return False
    
    try:
        import plotly
        print("✅ Plotly:", plotly.__version__)
    except ImportError:
        print("❌ Plotly 未安装")
        return False
    
    return True

def test_data_structure():
    """测试数据目录结构"""
    print("\n🔍 测试数据目录结构...")
    
    base_path = Path("../data/test_set")
    
    if not base_path.exists():
        print(f"❌ 数据目录不存在: {base_path}")
        return False
    
    print(f"✅ 数据目录存在: {base_path}")
    
    # 检查各个子目录
    required_dirs = {
        "pdf_reports": "PDF文件目录",
        "debug_data": "调试数据目录",
        "databases": "数据库目录"
    }
    
    for dir_name, desc in required_dirs.items():
        dir_path = base_path / dir_name
        if dir_path.exists():
            files_count = len(list(dir_path.rglob("*")))
            print(f"✅ {desc}: {dir_path} ({files_count} 个文件)")
        else:
            print(f"❌ {desc}不存在: {dir_path}")
    
    # 检查答案文件
    answer_files = list(base_path.glob("answers_*.json"))
    print(f"✅ 找到 {len(answer_files)} 个答案文件:")
    for file in answer_files:
        print(f"   - {file.name}")
    
    return True

def test_data_loading():
    """测试数据加载功能"""
    print("\n🔍 测试数据加载功能...")
    
    try:
        # 添加当前目录到Python路径
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        
        from components.data_loader import RAGResultsLoader
        
        # 创建数据加载器
        loader = RAGResultsLoader("../data/test_set")
        
        # 测试文档扫描
        docs = loader.get_available_documents()
        print(f"✅ 找到 {len(docs)} 个PDF文档: {docs}")
        
        # 测试配置扫描
        configs = loader.get_available_configs()
        print(f"✅ 找到 {len(configs)} 个配置: {configs}")
        
        if docs:
            # 测试单个文档信息
            doc_id = docs[0]
            doc_info = loader.get_document_info(doc_id)
            print(f"✅ 文档 {doc_id} 信息:")
            print(f"   - PDF存在: {doc_info.get('pdf_exists')}")
            print(f"   - 大小: {doc_info.get('pdf_size_mb')} MB")
            print(f"   - 解析完成: {doc_info.get('parsing_exists')}")
            
            # 测试数据加载
            parsing_data = loader.load_parsing_results(doc_id)
            if parsing_data:
                print(f"✅ 成功加载解析数据，包含 {len(parsing_data)} 个字段")
            else:
                print("⚠️ 解析数据为空")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入组件失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 数据加载测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 RAG Challenge 可视化系统环境测试")
    print("=" * 50)
    
    # 测试Python包
    imports_ok = test_imports()
    
    # 测试数据结构
    data_ok = test_data_structure()
    
    # 测试数据加载
    loading_ok = test_data_loading()
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"   Python包导入: {'✅ 通过' if imports_ok else '❌ 失败'}")
    print(f"   数据目录结构: {'✅ 通过' if data_ok else '❌ 失败'}")
    print(f"   数据加载功能: {'✅ 通过' if loading_ok else '❌ 失败'}")
    
    if imports_ok and data_ok and loading_ok:
        print("\n🎉 所有测试通过！可以启动可视化系统:")
        print("   python run.py")
    else:
        print("\n⚠️ 部分测试失败，请检查:")
        if not imports_ok:
            print("   1. 安装依赖: pip install -r requirements_viz.txt")
        if not data_ok:
            print("   2. 确保数据目录完整")
        if not loading_ok:
            print("   3. 检查组件代码是否有错误")

if __name__ == "__main__":
    main() 