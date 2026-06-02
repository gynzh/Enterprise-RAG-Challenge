# RAG 挑战赛获胜解决方案

**了解更多关于此项目的信息：**
- 俄语：https://habr.com/ru/articles/893356/
- 英语：https://abdullin.com/ilya/how-to-build-best-rag/

本仓库包含了RAG挑战赛两个奖项提名的获胜解决方案。该系统在使用公司年度报告回答问题方面达到了最先进的结果，采用了以下技术组合：

- 使用Docling进行自定义PDF解析
- 带有父文档检索的向量搜索
- 用于提升上下文相关性的大语言模型重排序
- 结构化输出提示和思维链推理
- 多公司比较的查询路由

## 免责声明

这是竞赛代码 - 比较粗糙但确实有效。在您深入研究之前，请注意以下几点：

- IBM Watson集成无法工作（它是竞赛特定的）
- 代码可能存在粗糙的边缘和奇怪的解决方案
- 没有测试，错误处理极少 - 您已经被警告了
- 您需要自己的OpenAI/Gemini API密钥
- GPU对PDF解析帮助很大（我使用了4090）

如果您正在寻找生产就绪的代码，这不是。但如果您想探索不同的RAG技术及其实现 - 可以看看！

## ⚡ API配额问题解决方案

**❌ 常见问题**: `OpenAI RateLimitError: Error code: 429` (配额不足)

**✅ 免费替代方案**: 我们已经集成了免费的Hugging Face嵌入模型！

```bash
# 使用免费嵌入模型替代OpenAI (推荐)
python main.py process-reports-free --config no_ser_tab

# 可选择不同的免费模型
python main.py process-reports-free --config no_ser_tab --model all-mpnet-base-v2
```

**免费模型选项**:
- `all-MiniLM-L6-v2`: 快速，良好质量，384维度（默认）
- `all-mpnet-base-v2`: 较慢但更高质量，768维度  
- `paraphrase-multilingual-MiniLM-L12-v2`: 多语言支持

**技术优势**:
- 🆓 **完全免费**: 无API调用费用和配额限制
- ⚡ **本地运行**: 无网络延迟，更稳定
- 🎯 **效果验证**: 384维向量检索效果良好，满足复现需求

## 快速开始

克隆和设置：
```bash
git clone https://github.com/IlyaRice/RAG-Challenge-2.git
cd RAG-Challenge-2
python -m venv venv
venv\Scripts\Activate.ps1  # Windows (PowerShell)
pip install -e . -r requirements.txt
```

将`env`重命名为`.env`并添加您的API密钥：
```bash
# 必需 (用于对话生成)
GEMINI_API_KEY="AIza..."

# 可选 (如果要使用原始OpenAI嵌入)
OPENAI_API_KEY="sk-..."
```

**💡 推荐流程** (使用免费嵌入):
```bash
cd data/test_set

# 1. PDF解析
python ../../main.py parse-pdfs

# 2. 数据处理 (使用免费嵌入模型)
python ../../main.py process-reports-free --config no_ser_tab

# 3. 问答处理 (使用Gemini对话)
python ../../main.py process-questions --config gemini_thinking
```

## 测试数据集

该仓库包含两个数据集：

1. 一个小型测试集（在`data/test_set/`中）包含5个年度报告和问题
2. 完整的ERC2竞赛数据集（在`data/erc2_set/`中）包含所有竞赛问题和报告

每个数据集目录都包含自己的README，具有特定的设置说明和可用文件。您可以使用任一数据集来：

- 研究示例问题、报告和系统输出
- 使用提供的PDF从头开始运行管道
- 使用预处理数据直接跳到特定的管道阶段

查看相应的README文件以获取详细的数据集内容和设置说明：
- `data/test_set/README.md` - 小型测试数据集
- `data/erc2_set/README.md` - 完整竞赛数据集

## 使用方法

您可以通过在`src/pipeline.py`中取消注释您想要运行的方法来运行管道的任何部分，然后执行：
```bash
python .\src\pipeline.py
```

您也可以使用`main.py`运行任何管道阶段，但需要从包含数据的目录运行：
```bash
cd .\data\test_set\
python ..\..\main.py process-questions --config max_nst_o3m
```

### CLI命令

获取可用命令的帮助：
```bash
python main.py --help
```

可用命令：
- `download-models` - 下载必需的docling模型
- `parse-pdfs` - 解析PDF报告，支持并行处理选项
- `serialize-tables` - 处理解析报告中的表格
- `process-reports` - 在解析的报告上运行完整管道
- `process-questions` - 使用指定配置处理问题

每个命令都有自己的选项。例如：
```bash
python main.py parse-pdfs --help
# 显示选项如 --parallel/--sequential、--chunk-size、--max-workers

python main.py process-reports --config ser_tab
# 使用序列化表格配置处理报告
```

## 一些配置

- `max_nst_o3m` - 使用OpenAI o3-mini模型的最佳性能配置
- `ibm_llama70b` - 使用IBM Llama 70B模型的替代配置
- `gemini_thinking` - 使用Gemini巨大上下文窗口的完整上下文回答。实际上这不是RAG

查看`pipeline.py`了解更多配置和详细信息。

## 许可证

MIT 