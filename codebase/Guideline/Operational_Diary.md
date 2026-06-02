# RAG 复现操作日记

本文档是一本详细的操作手册，旨在指导用户从零开始完整复现RAG优胜方案。它为拥有本地GPU和需要使用云端GPU的用户分别提供了清晰的环境配置路径。

---

## Part 1: 环境配置 (请根据自身情况二选一)

在开始之前，请评估您是否拥有带CUDA环境的本地NVIDIA GPU，并根据您的具体情况选择相应的配置路径。

- **如果你有本地GPU** -> **请遵循 `选项A`**
- **如果你没有本地GPU** -> **请遵循 `选项B`**

---

### 选项A：本地GPU环境配置

此路径适用于已拥有兼容NVIDIA GPU及CUDA环境的用户。

```powershell
# 1. 创建Python虚拟环境
# 在您计划存放项目的目录下执行
python -m venv venv

# 2. 激活虚拟环境
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

# 3. 安装适配本地CUDA的PyTorch
# !!! 关键步骤 !!!
# 项目原要求 torch==2.0.0，但这可能与你的新版CUDA不兼容。
# 请访问 PyTorch 官网 (https://pytorch.org/get-started/locally/)
# 根据您自己的CUDA版本，找到最接近 torch==2.1.0 的版本并获取安装命令。
# 以下命令以CUDA 12.1为例：
pip3 install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121
```
**基础环境配置完成后，请继续执行 [Part 2: 项目设置与数据准备](#part-2-项目设置与数据准备-通用步骤)。**

---

### 选项B：云端GPU环境配置

此路径适用于没有本地GPU，需要租用云端资源的用户。以下步骤以 [Glows.ai](https://Glows.ai) 平台为例。

#### 1. 云端资源选择与连接
- **资源**: 在云服务商处选择带有 **NVIDIA GPU** 的实例，并确保镜像包含 **CUDA** 和 **Python 3.11+**（例如 `CUDA12.4 Base` 镜像）。
- **连接**: 为了稳定连接，强烈建议在本地 VS Code 中使用SSH配置文件 (`Remote-SSH: Open SSH Configuration File...`) 并通过别名连接到您的远程主机。

#### 2. 在云端配置基础环境
当您成功连接到云主机后，执行以下命令：
```bash
# 1. 系统更新与Git安装 (如果镜像不包含)
apt update
apt install git -y

# 2. 创建虚拟环境
# 在您计划存放项目的目录下执行
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 安装适配云端CUDA的PyTorch
# 由于RTX 4090等新GPU需要较新的CUDA，我们选择安装与之兼容的torch==2.1.0版本。
pip3 install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121
```
**基础环境配置完成后，请继续执行以下步骤。**

---

## Part 2: 项目设置与数据准备 (通用步骤)

无论您使用本地还是云端环境，接下来的步骤都是相同的。

### 1. 克隆项目仓库与安装依赖
```bash
# 1. 克隆代码到当前目录
git clone https://github.com/IlyaRice/RAG-Challenge-2.git

# 2. 进入项目目录
cd RAG-Challenge-2

# 3. 安装项目特定的依赖
# (此时PyTorch已安装，pip会自动跳过)
pip install -e . -r requirements.txt
```

### 2. 数据准备与清理
为了确保从零开始完整复现，请手动删除 `data/test_set/` 目录下任何可能存在的 `databases` 和 `debug_data` 两个子文件夹。
- **理由**: 这两个文件夹包含作者预处理好的中间结果。删除它们可以保证复现的每一步都使用自己生成的数据。

同时，为了加速初步测试流程，建议从 `data/test_set/pdf_reports/` 目录中删减PDF报告数量，可仅保留两份进行首轮端到端测试。
- **理由**: 使用较少的数据量可以显著缩短每个阶段的执行时间，便于快速迭代和调试。

---

## Part 3: 核心流水线执行 (通用步骤)

### 1. 准备API密钥
在项目根目录下 (`RAG-Challenge-2/`)，创建 `.env` 文件并填入您的API密钥。
```bash
# 警告：请勿直接在命令行中暴露密钥，建议使用编辑器创建
nano .env
```
`.env`文件内容示例:
```
OPENAI_API_KEY="sk-..."
GEMINI_API_KEY="AIza..."
JINA_API_KEY="jina_..."
```

### 2. 执行PDF解析
此步骤将利用GPU对PDF进行解析，并将结构化结果存为JSON文件。
```bash
# 1. 切换到测试数据目录
cd data/test_set

# 2. 从项目根目录执行解析命令
python ../../main.py parse-pdfs
```
- **预期结果**: 命令成功执行，解析后的文件将出现在新建的`debug_data/parsed_reports/`目录中。


### 3. 序列化表格 (可选但推荐)
此步骤将解析出的表格转换为对LLM更友好的格式。
```bash
# (仍在 data/test_set 目录下)
python ../../main.py serialize-tables
```
- **预期结果**: 命令执行成功，`debug_data`中会生成包含序列化表格的新JSON文件。

### 4. 数据注入 (创建数据库)
此步骤是RAG的核心之一，它会读取解析后的文本，通过API生成向量，并构建本地检索引擎。
```bash
# (仍在 data/test_set 目录下)
# --config no_ser_tab 表示使用未序列化表格的数据
python ../../main.py process-reports --config no_ser_tab
```
- **预期结果**: 命令执行时间较长，因为它会为大量文本块调用Embedding API。成功后，`databases`目录下会生成新的FAISS和BM25索引文件。

### 5. 处理问题 (执行RAG问答)
这是最后一步，模拟用户提问，并使用我们构建的RAG系统来生成答案。
```bash
# (仍在 data/test_set 目录下)
# --config max_nst_o3m 是原作者效果最好的配置之一
python ../../main.py process-questions --config max_nst_o3m
```
- **预期结果**: 系统会处理测试集中的问题，并最终在`debug_data/`相应目录中生成包含答案的JSON文件。

---

## Part 4: 保存工作与同步 (通用步骤)

这部分详细说明了如何将所有代码和文档的变更安全地推送到你自己的GitHub仓库。

### 1. 将项目连接到你的GitHub仓库
```bash
# 1. 检查当前的远程地址 (应为原作者仓库)
git remote -v

# 2. 将 'origin' 的URL更改为你自己的仓库地址
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 3. 再次检查以确认更改
git remote -v
```

### 2. 推送变更到你的GitHub
```bash
# 1. 添加所有变更到暂存区
git add .

# 2. 配置Git身份 (首次在新环境中提交时需要)
git config user.email "xx@gmail.com"
git config user.name "xxx"

# 3. 提交变更
git commit -m "feat: 完成第一版流程"

# 4. 推送到GitHub
git push -u origin main
``` 

---

## 附录：混合工作流指南 (云端GPU解析 + 本地CPU执行)

本部分为特殊场景提供指导：您已在云端GPU服务器上完成了计算最密集的第一步（PDF解析），并希望在没有GPU的本地个人电脑上继续执行后续步骤。

### 核心挑战与解决方案

- **挑战**: 您在云端安装的PyTorch是为NVIDIA GPU编译的（依赖CUDA工具包）。在没有GPU的本地电脑上，这个版本的PyTorch无法安装或运行。
- **解决方案**: 在本地电脑上，我们必须安装**纯CPU版本**的PyTorch。它功能完整，只是所有计算都由CPU完成。对于后续主要依赖API调用的步骤来说，这完全足够。

### 本地复现步骤

1.  **同步代码**: 确保您已将云端的所有代码和解析好的`debug_data`文件夹通过Git推送到您的GitHub仓库，然后在本地电脑上 `git pull` 或 `git clone` 最新的版本。

2.  **创建本地虚拟环境**:
    ```bash
    # 在项目目录下
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\Activate.ps1 # Windows
    ```

3.  **安装CPU版PyTorch**:
    ```bash
    # 这是关键区别！此命令不依赖任何GPU驱动。
    pip install torch torchvision torchaudio
    ```

4.  **安装其余依赖**:
    ```bash
    # pip会自动跳过已安装的torch
    pip install -e . -r requirements.txt
    ```

5.  **继续流水线**:
    - 在本地项目根目录创建 `.env` 文件并填入您的API密钥。
    - 您现在可以从 `Part 3` 中的第3步（序列化表格）或第4步（数据注入）开始，继续执行所有剩余的命令。 

---

## 附录：强制全量推送覆盖命令

### 问题背景
项目中的`.gitignore`文件忽略了重要的中间文件目录：
```
data/test_set/debug_data
data/test_set/databases
data/erc2_set/debug_data  
data/erc2_set/databases
```

这些目录包含了**复现过程的关键中间产物**，对于学习和验证非常重要。

### 🚨 强制全量推送覆盖命令

**步骤1: 强制添加所有文件（包括被忽略的）**
```bash
# 进入项目根目录
cd RAG_Challenge_Reproducibility

# 强制添加所有文件，包括.gitignore忽略的文件
git add -A
git add -f data/test_set/debug_data/
git add -f data/test_set/databases/
git add -f data/erc2_set/debug_data/
git add -f data/erc2_set/databases/

# 检查添加状态
git status --porcelain | head -20
```

**步骤2: 提交所有更改**
```bash
# 提交所有文件（包括中间产物）
git commit -m "feat: 完整项目数据 - 包含所有中间处理文件和数据库"
```

**步骤3: 强制推送覆盖远程仓库**
```bash
# 方法1: 普通推送 (推荐)
git push origin main

# 方法2: 强制推送 (谨慎使用)
git push --force-with-lease origin main

# 方法3: 完全强制覆盖 (最后手段)
git push --force origin main
```

### 📊 验证推送结果

**检查推送状态**:
```bash
# 确认本地和远程同步
git status

# 查看最新提交
git log --oneline -3

# 验证重要文件是否在远程
git ls-remote --heads origin
```

**验证关键文件存在**:
```bash
# 检查中间文件是否被正确跟踪
git ls-files | grep -E "(debug_data|databases)" | head -10

# 确认文件大小合理
du -sh data/test_set/debug_data/
du -sh data/test_set/databases/
```

### ⚠️ 重要提醒

1. **强制推送风险**: `--force`命令会覆盖远程历史，请确保您有权限
2. **文件大小**: 中间文件可能较大，确保网络条件良好
3. **备份建议**: 推送前建议备份本地重要修改
4. **协作影响**: 如果多人协作，强制推送会影响其他贡献者

### 🎯 推荐的完整操作序列

```bash
# 一站式强制全量推送序列
cd RAG_Challenge_Reproducibility

# 添加所有文件（包括忽略的）
git add -A
git add -f data/*/debug_data/ data/*/databases/

# 提交
git commit -m "feat: 完整项目 - 所有源码、文档、中间文件和数据库"

# 推送
git push origin main

# 验证
git status && echo "✅ 推送完成！"
```

### 🔍 故障排除

**如果推送被拒绝**:
```bash
# 拉取最新更改后再推送
git pull --rebase origin main
git push origin main
```

**如果文件过大**:
```bash
# 使用Git LFS管理大文件
git lfs track "*.faiss" "*.json"
git add .gitattributes
git commit -m "feat: 添加Git LFS支持"
git push origin main
```

**如果需要清理历史**:
```bash
# 清理大文件历史 (谨慎使用)
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch data/*/databases/*.faiss' \
--prune-empty --tag-name-filter cat -- --all
``` 