# Python + Pytest + Paramiko + Allure + Jenkins 集成测试 Demo

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Pytest](https://img.shields.io/badge/pytest-9.0%2B-green)
![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-red)
![Allure](https://img.shields.io/badge/Allure-Reporting-orange)
![uv](https://img.shields.io/badge/uv-Package%20Manager-purple)

一个端到端的 Paramiko (SSH/SFTP) 集成测试工程实践 Demo。从本地 pytest 单测 → Jenkins Pipeline CI/CD → Allure 可视化报告，简单复现之前在汇丰测试团队的自动化测试工作流。

> 🏢 **背景**: 项目设计重现并优化汇丰软件开发内部 QA 团队的自动化测试和 CI/CD 流程，目标是构建一个可直接用于面试展示的、"企业级可迁移"的测试工程样例。

---

## ✨ 项目亮点

| #   | 亮点                     | 对企业的价值                                                        |
| --- | ------------------------ | ------------------------------------------------------------------- |
| 1   | **完整 CI/CD Pipeline**  | Jenkins 从 GitHub 拉取代码 → 自动配置依赖 → 执行测试 → 生成双份报告 |
| 2   | **双报告体系**           | pytest-html (快速预览) + Allure (结构化可视化仪表盘)                |
| 3   | **Allure 装饰器**        | 测试用例按 `feature / story` 分组，直接映射产品需求                 |
| 4   | **pytest-rerunfailures** | 集成测试天生有网络抖动，自动重跑避免偶发失败                        |
| 5   | **凭据安全管理**         | Jenkins Credentials + `withCredentials` 注入，密码绝不硬编码        |
| 6   | **Markers 分类**         | `smoke` / `integration` / `perf` 标记支持选择性执行                 |
| 7   | **uv 包管理**            | 比 pip 快 10-100 倍，企业项目标准实践                               |
| 8   | **SFTP 性能基准测试**    | 2000 文件/90MB 串行上传/下载传输 + MD5 全量校验，规避 paramiko 线程安全风险  |

---

## 🏗️ 技术栈

```
├── 测试框架:     pytest (9.1+) + pytest-html + pytest-rerunfailures
├── 报告生成:     allure-pytest (2.16+)
├── 包管理:       uv
├── CI/CD:        Jenkins 2.580+ (Declarative Pipeline)
├── 目标服务:     WSL SSH (OpenSSH Server) on Windows
├── 远程客户端:   Paramiko 5.x
├── 配置管理:     python-dotenv
├── 代码质量:     ruff + black
└── 版本控制:     Git + GitHub
```

---

## 🔄 CI/CD 架构图

```
GitHub Repository
┌────────────────────────────────┐
│ 源代码 / Jenkinsfile / 测试用例 │
└──────────────┬─────────────────┘
               │ git clone
               ▼
Jenkins Agent (Windows)
┌──────────────────────────────────┐
│ ① Checkout SCM  (自动拉代码)      │
│ ② Verify Env    (工具版本确认)    │
│ ③ Install Deps  (uv sync)        │
│ ④ Run Tests     (withCredentials)│
│ ⑤ Publish HTML  (pytest-html)    │
│ ⑥ Generate Allure                │
│ ⑦ Archive Artifacts              │
└──────┬──────────────┬────────────┘
       │              │
       ▼              ▼
┌────────────┐   ┌──────────────┐
│ pytest-html│   │ Allure 仪表盘 │
│ report.html│   │ allure-report│
└────────────┘   └──────────────┘
```

![Allure 仪表盘总览](docs/images/allure-dashboard-overview.png)
> 👆 **Allure Dashboard**：4 个测试用例全部通过，Features 按 SSH 远程命令 / SFTP 文件传输分组，点击每个 Suite 可进入单条用例的执行步骤追溯

---

## 📁 目录结构

```
nelson-paramiko-tests/
├── Jenkinsfile                  # Jenkins Declarative Pipeline 定义
├── pyproject.toml               # 项目元数据 + pytest/ruff/black 配置 (单源配置)
├── uv.lock                      # uv 锁定依赖版本 (类似 package-lock.json)
├── .env.example                 # 环境变量模板 (SSH 凭据示例)
├── .gitignore                   # 忽略 .env / reports / allure-results 等
│
├── conftest.py                  # pytest fixtures (ssh_client / sftp_client / clean_up)
├── constants.py                 # 跨平台路径常量 (Windows ↔ WSL)
├── utils.py                     # MD5 校验 / 路径转换等工具函数
│
├── tests/                       # 测试用例目录 (testpaths)
│   ├── test_paramiko_run_command_success.py  # SSH 命令成功场景
│   ├── test_paramiko_run_command_fail.py     # SSH 命令失败场景
│   ├── test_paramiko_sftp_download.py        # SFTP 文件下载 (单文件)
│   ├── test_paramiko_sftp_upload.py          # SFTP 文件上传 (单文件)
│   └── test_performance_sftp_batch_transfer.py  # SFTP 性能基准 (2000 文件串行上传/下载)
│
├── test_data_files/             # 测试用数据文件
│   ├── source_data_files/       # 源文件 (上传 / 下载测试用)
│   └── destination_data_files/  # 目标文件 (生成后不自动清理，方便排查)
│
└── docs/
    └── CICD_FLOW.md             # CI/CD Pipeline 详细解读
```

---

## 🖥️ 本地环境准备

| #   | 工具       | 版本要求          | 安装方式                                                 | 验证                               |
| --- | ---------- | ----------------- | -------------------------------------------------------- | ---------------------------------- |
| 1   | Python     | 3.12+             | `uv python install 3.12`                                 | `python --version`                 |
| 2   | uv         | 最新              | `winget install astral-sh.uv`                            | `uv --version`                     |
| 3   | Java       | 17+               | `winget install Microsoft.OpenJDK.17`                    | `java -version`                    |
| 4   | Allure CLI | 2.46+             | scoop / GitHub releases                                  | `allure --version`                 |
| 5   | Git        | 2.x               | `winget install Git.Git`                                 | `git --version`                    |
| 6   | WSL        | 含 OpenSSH Server | Windows Features → 勾选 "适用于 Linux 的 Windows 子系统" | `wsl -e service ssh status`        |
| 7   | Jenkins    | 2.580+            | `winget install Jenkins.Jenkins`                         | 浏览器打开 `http://localhost:8080` |

### Jenkins 必需插件

| 插件           | 作用                            |
| -------------- | ------------------------------- |
| Pipeline       | Declarative Pipeline 骨架       |
| Git Plugin     | 拉取 GitHub 代码                |
| Allure         | 生成 Allure 仪表盘              |
| HTML Publisher | 在 Jenkins 页面嵌入 pytest-html |
| Timestamper    | Console Output 加时间戳         |

### Jenkins Global PATH 配置

Jenkins 作为 Windows 服务运行，PATH 与 PowerShell 不同。在 **Manage Jenkins → System → Global properties → Environment variables** 添加：

```
PATH = C:\Users\<你的用户名>\.local\bin;H:\allure-2.46.0\bin;C:\Python314;C:\Python314\Scripts;%PATH%
```

### Jenkins Tools 配置

**Manage Jenkins → Tools**：

| Section                                       | Value                                             |
| --------------------------------------------- | ------------------------------------------------- |
| Git installations → Path to Git executable    | `C:\Program Files\Git\cmd\git.exe` (你的实际路径) |
| Allure installations → Name                   | `allure-2.46`                                     |
| Allure installations → Installation directory | `H:\allure-2.46.0`                                |

### Jenkins Credentials

**Manage Jenkins → Credentials → Global → Add Credentials**：

| Field    | Value                  |
| -------- | ---------------------- |
| Kind     | Username with password |
| ID       | `paramiko-ssh-creds`   |
| Username | 你的 WSL SSH 用户名    |
| Password | 你的 WSL SSH 密码      |

> ⚠️ ID 必须和 Jenkinsfile 里 `withCredentials` 的 `credentialsId` 完全一致。

---

## 🚀 本地运行

```bash
# 1. 克隆仓库
git clone <你的 GitHub 仓库地址>
cd nelson_paramiko_test_with_pytest_paramiko_allure_jenkins

# 2. 安装依赖
uv sync --all-extras

# 3. 配置 SSH 凭据（不要提交 .env）
# Windows PowerShell:
Copy-Item .env.example .env
# Linux/Mac:
# cp .env.example .env

# 编辑 .env 填入真实的 SSH_USER / SSH_PWD

# 4. 跑全量测试（含 rerun 重跑 + pytest-html + allure-results）
uv run pytest

# 5. 生成 Allure 静态报告
allure generate allure-results -o allure-report --clean

# 6. 本地预览 Allure 仪表盘
allure open allure-report
```

### 选择性执行

```bash
# 只跑冒烟测试
uv run pytest -m smoke

# 只跑集成测试
uv run pytest -m integration

# 只跑性能基准测试（会生成 2000 个临时文件，需要 WSL SSH 连接）
uv run pytest -m perf

# 只跑单个测试文件
uv run pytest tests/test_paramiko_sftp_download.py -v
```

### pytest markers

| Marker        | 说明                       | 测试数量      |
| ------------- | -------------------------- | ------------- |
| `smoke`       | 冒烟测试 — 仅 SSH 命令     | 2 / 6         |
| `integration` | 集成测试 — 覆盖 SSH + SFTP | 4 / 6         |
| `perf`        | 性能测试 — 2000 文件批量传输 | 2 / 6         |

Markers 定义在 `pyproject.toml → [tool.pytest.ini_options] → markers`。

---

## 🔧 Jenkins CI/CD Pipeline

Jenkinsfile 定义了 5 个 Stage + Declarative Checkout SCM。详细代码解读见 [`docs/CICD_FLOW.md`](docs/CICD_FLOW.md)。

| Stage                      | 核心动作                              | 关键技术点                                     |
| -------------------------- | ------------------------------------- | ---------------------------------------------- |
| **Checkout SCM**           | 自动从 GitHub 拉取代码                | Jenkins Git Plugin，凭据 Token 认证            |
| **Verify Environment**     | 打印 python / uv / allure 版本        | 快速诊断 PATH 问题                             |
| **Install Dependencies**   | `uv sync --all-extras`                | 比 pip 快 100x，lock 文件保证可重现            |
| **Run Tests**              | `withCredentials` 注入 SSH → `pytest` | 密码自动打码，rerun 防止偶发失败               |
| **Publish HTML Report**    | `HTML Publisher` 插件                 | pytest-html 报告嵌入 Jenkins 页面              |
| **Generate Allure Report** | `allure` step                         | 新版 Allure Plugin（org.allurereport.jenkins） |

![Jenkins Build 全绿 Stage 视图](docs/images/jenkins-build-green.png)
> 👆 **Jenkins Pipeline 执行结果**：5 个 Stage 全部绿色通过，`Run Tests` 阶段显示 pytest 成功，`Generate Allure Report` 阶段报告生成无异常

### Jenkins Pipeline Job 配置

1. Jenkins 主页 → **New Item**
2. **Name**: `paramiko-tests`
3. **Type**: Pipeline → OK
4. **Pipeline Section**:
   - Definition: **Pipeline script from SCM**
   - SCM: Git
   - Repository URL: 你的 GitHub HTTPS URL
   - Credentials: 你的 GitHub Token（如果私有仓库）
   - Branch Specifier: `*/main`
   - Script Path: `Jenkinsfile`（不要改）
5. Save → **Build Now**

---

## 📊 报告类型说明

| 报告            | 生成方式                                         | 位置                       | 特点                                               |
| --------------- | ------------------------------------------------ | -------------------------- | -------------------------------------------------- |
| **pytest-html** | `--html=reports/report.html`                     | `reports/report.html`      | 单文件、快速预览、Jenkins HTML Publisher 嵌入      |
| **Allure**      | `--alluredir=allure-results` + `allure generate` | `allure-report/index.html` | 结构化仪表盘、feature/story 分组、趋势图、历史对比 |
| **测试日志**    | `log_file = "reports/test_run.log"`              | `reports/test_run.log`     | 完整 INFO 级别日志，调试问题首选                   |

![pytest-html 报告预览](docs/images/pytest-html-report.png)
> 👆 **pytest-html 报告**：与 Allure 形成互补——单文件 HTML 直接预览，快速定位失败用例；Allure 则提供跨构建的历史趋势和结构化分析

### Allure 仪表盘亮点

- **Feature 分组**: 按 `SSH 远程命令` / `SFTP 文件传输` 展示
- **Story 层级**: 每个 feature 下按成功/失败、上传/下载分组
- **趋势图**: 多次构建的通过率变化
- **步骤追溯**: 每个失败用例可以看到具体哪步报错

---

## ⚡ SFTP 性能基准测试

性能测试文件: `tests/test_performance_sftp_batch_transfer.py`

### 测试目标

**功能正确性 + 性能指标双维度验收**：2000 个文件（90MB 总量）的串行 SFTP 上传和下载，每个文件都校验文件大小 + MD5 hash，同时统计完整的性能指标。

### 文件规格（4 批次，总计 2000 个）

| 批次 | 数量  | 单文件大小 | 累计体积 |
| ---- | ----- | ---------- | -------- |
| 1    | 1000  | 10 KB      | ~10 MB   |
| 2    | 500   | 20 KB      | ~10 MB   |
| 3    | 300   | 100 KB     | ~30 MB   |
| 4    | 200   | 200 KB     | ~40 MB   |
| **合计** | **2000** | — | **~90 MB** |

### 验收标准

| 指标          | 阈值   | 说明                                         |
| ------------- | ------ | -------------------------------------------- |
| 传输成功率    | 100%   | 任何一个文件校验失败即整体 FAIL              |
| 上传总耗时    | < 300s | 5 分钟以内                                   |
| 下载总耗时    | < 300s | 5 分钟以内                                   |
| 性能统计维度  | 全量   | 总耗时 / 平均单文件 / P95 / 各批次独立耗时   |

### 关键设计决策

#### 1. 串行执行：规避 paramiko SFTPClient 线程安全风险

```python
# paramiko 官方文档明确标注: SFTPClient is NOT thread-safe
# 多线程共享同一个 SSHClient / SFTPClient 会导致底层 channel 乱序、数据损坏甚至死锁

for batch in upload_test_files:  # 外层: 批次循环
    for local_path in batch["files"]:  # 内层: 单文件循环（串行 put/get）
        sftp.put(str(local_path), remote_path)
        # 校验文件大小 + MD5
```

**为什么不做并发？** paramiko 的 SFTP 通道底层是 SSH 的同一个 channel，多线程读写会导致 frame 边界错乱。Java / Go 的 SFTP 库通常有真正的连接池和多连接并发能力，但 paramiko 在 Python 生态里没有安全的多线程方案。串行虽然慢，但正确性 100%。预留了扩展点：如果要做并发，需要每个 worker 独立建立 SSHConnection + SFTPClient，不能共享。

#### 2. 独立连接：不复用 conftest.py 的 session fixture

```python
# conftest.py 里的 ssh_client / sftp_client 是单例，给功能测试用的
# 性能测试自己建独立连接（scope="session"），超时参数 30s（比 conftest 的 10s 宽松）


@pytest.fixture(scope="session")
def perf_ssh_connection() -> Iterator[paramiko.SSHClient]:
    ssh = paramiko.SSHClient()
    ssh.connect(_HOST, timeout=30, banner_timeout=30, auth_timeout=30)
    yield ssh
    ssh.close()
```

**为什么独立？** 第一，连接隔离——性能测试和功能测试互不影响；第二，Jenkins CI 环境网络延迟更高，需要更宽松的 timeout；第三，为未来并发扩展留好干净的边界。

#### 3. Jenkins Pipeline 超时调整

```groovy
// Jenkinsfile 顶层 options
options {
    timeout(time: 10, unit: 'MINUTES')   // 之前 3 分钟会导致 perf suite 被强杀
    ...
}
```

性能测试 2000 个文件 + 每个文件一次远程 `md5sum` exec_command，串行耗时约 2-5 分钟。3 分钟 timeout 会在 Jenkins 上被强杀，调到 10 分钟留够余量。

#### 4. 临时文件生命周期管理

```python
# 本地 source 文件: fixture 里生成 → yield 测试 → fixture 清理（delete unlink）
# 本地 destination 文件: 下载测试后 fixture 清理（glob + unlink）
# 远程 WSL 目录: /tmp/perf_test_{ts}_{rand} → yield → rm -rf
```

**为什么这样设计？** 失败也要清理——用 try/finally 模式，测试中途崩了也不会在 `test_data_files/` 里残留几千个文件污染数据目录。远程目录用随机名避免并发 session 冲突。

### 性能统计方法

```python
# P95 计算（标准 Python 实现，无需额外依赖）
def _compute_percentile(sorted_durations: List[float], p: float) -> float:
    idx = int(len(sorted_durations) * p / 100)
    return sorted_durations[idx]


# 每个文件独立计时
file_start = time.perf_counter()  # 纳秒精度，不受系统时钟调整影响
sftp.put(local, remote)
file_elapsed = time.perf_counter() - file_start

# 输出 Markdown 表格到 Allure 附件
stats = _format_stats_summary(batch_results, all_durations)
allure.attach(stats, name="上传性能统计", attachment_type=_ALLURE_MD_ATTACHMENT_TYPE)
```

**用 `perf_counter()` 而不是 `time.time()`？** `time.time()` 受系统时钟调整影响（NTP 同步可能会跳），`perf_counter()` 是单调递增的高精度计时器，专门用来做耗时测量。

### 运行方式

```bash
# 本地跑性能测试
uv run pytest -m perf -v

# Jenkins 参数化触发: TEST_SUITE = perf
# 耗时 2-5 分钟，Jenkinsfile timeout 设为 10 分钟
```

---

## ⚠️ 常见问题 FAQ

**Q: Jenkins 构建时报 `'git' is not recognized`？**
A: Jenkins Git Plugin 内部用绝对路径调用 git.exe，但不会加到 Jenkins PATH。解决方案：在 Jenkins Global PATH 里加 git 目录，或者不在 Verify Environment 里调用 git。

**Q: Jenkins Build 失败，全是 `ClassCastException`？**
A: 99% 是 Allure Plugin 版本和 Jenkinsfile 参数类型不匹配。读堆栈第一行：`expected XXX but received YYY` —— 直接告诉你要什么类型。新版 Allure Plugin（org.allurereport.jenkins）的 `results` 是 `[[path: 'xxx']]` 对象数组，`report` 是单个字符串。

**Q: Jenkins 里 `withCredentials` 怎么工作的？**
A: 进入块时 Jenkins 从 Credentials Store 解密密码 → 设置环境变量 SSH_USER/SSH_PWD → 执行命令 → 退出块立即清除。Console Output 里密码会自动打码。Python 里 `os.getenv()` 直接取值。

**Q: 为什么不把 .env 提交到 git？**
A: `.env` 包含明文密码。`.env.example` 里放占位符（`your_username_here`），新人 clone 后复制一份改成自己的。

**Q: `pytest-rerunfailures` 和 Jenkins `post { failure }` 重跑有什么区别？**
A: pytest-rerunfailures 在同一个 Stage 内重跑，用例级别重试；Jenkins failure 重跑是整个 Pipeline 重新执行。企业里两个都会配，但 pytest 插件级别更精细。

**Q: 为什么用 `uv` 不用 `pip`？**
A: `uv` 由 Astral（ruff 团队）开发，Python 包管理全链路比 pip 快 10-100x。银行 CI Pipeline 对构建时间非常敏感 —— 快 1 分钟就是 100 个 Job 每天省 1.6 小时。

---

## 🤝 关于这个项目

### 这个项目的测试覆盖范围来源

这个 Demo 是我回顾之前银行测试项目中的Python + Pytest + Paramiko + Allure + Jenkins 过程中的完整实践记录。

### 关于smoke(冒烟测试)/integration(集成测试)的覆盖范围

这个项目中的smoke/integration测试主要涉及到一些基本操作的元动作, 用来做基本smoke/integration测试的演示, 实际工作中会基于这些元动作组合出更具体的测试过程. 另外, 实际工作中用到的测试过程涉及更多的针对真实场景的测试动作, 比如
- 预检测服务器状态以及测试所需服务的状态
- 预检测Database中测试条目所需配置是否已经是enable状态
- 预检测测试环境所需目录及权限是否存在且可读写
- 自动生成测试所需文件
- 轮询检测上游文件的处理情况, 超时自动判定为测试失败
- 轮询检测下游文件的收取情况, 超时自动判定为测试失败
- 返回测试结果接入Jenkins Pipeline Job, 并根据结果判断build成功/失败

### 关于performance(性能基准测试)测试的覆盖范围

性能测试部分尽量还原了过往真实工作中的测试场景, 并且加以改进, 增加了更多的性能基准方面的评测.

**作者**: Nelson Wang  
**灵感来源**: 汇丰软件开发（广东）QA 团队 日常实践
