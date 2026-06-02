#!/usr/bin/env python3
# 这个命令使还脚本能在UNIX下通过./run.py直接启动（脚本解释器会到环境变量中找到对应的pythons来运行这个脚本）
"""
RAG Challenge 复现结果可视化启动脚本

使用方法:
python run.py

或者:
python -m visualization.run
"""

# sys.path是python查找模块的路径列表
import sys
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(current_dir)) # 插入列表最前面
sys.path.insert(0, str(project_root))

try:
    from app import main
    
    if __name__ == "__main__": # 判断当前文件是被直接运行，而不是被别的文件导入
        print("🚀 启动 RAG Challenge 复现结果可视化...")
        print("=" * 50)
        main()

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("\n请确保已安装所有依赖:")
    print("pip install -r requirements_viz.txt")
    
except Exception as e:
    print(f"❌ 启动失败: {e}")
    print("\n请检查:")
    print("1. 数据目录是否存在: ../data/test_set")
    print("2. 依赖是否已安装: pip install -r requirements_viz.txt")
    print("3. 是否在正确的目录下运行脚本") 