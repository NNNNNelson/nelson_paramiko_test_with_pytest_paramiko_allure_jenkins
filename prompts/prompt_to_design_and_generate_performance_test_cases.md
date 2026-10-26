# 【角色 Role】
你是一名资深 Python 测试工程师，熟悉 pytest fixture 体系、paramiko SFTP 协议限制、性能测试方法论，Allure 报告集成以及Jenkins。你深知 paramiko 的 SFTPClient 对象不是线程安全的，不能被多线程共享使用。

# 【项目上下文 Context】
以下是我项目的关键信息，请严格基于这些信息生成代码：

## 技术栈
- Python 3 + pytest + paramiko (SFTP) + Allure
- 运行环境: Windows 本机（测试客户端） + WSL Ubuntu（SSH/SFTP 服务器）
- CI: Jenkins

## 现有 fixture（位于 conftest.py）
- `ssh_client` (scope="session"): paramiko.SSHClient 单例连接
- `sftp_client` (scope="session"): 基于 ssh_client 创建的 paramiko.SFTPClient 单例
- 注意: 这两个 fixture 都是 session 级单例，**不可用于多线程并发场景**

## 现有工具函数（位于 utils.py）
- `local_file_md5(file_path)`: 分块计算本地文件 MD5
- `remote_file_md5(ssh_client, remote_path)`: 通过 md5sum 命令获取远程文件 MD5

## 代码风格参考
- 已有测试用例在 tests/test_paramiko_sftp_upload.py 和 test_paramiko_sftp_download.py
- 使用 allure.feature / allure.story / allure.title 装饰器
- 日志统一用 logging.getLogger(__name__)
- 文件路径通过 constants.py 管理，不要硬编码

# 【需求 Spec】
请编写两个性能测试用例：批量上传 2000 个文件 + 批量下载 2000 个文件。

## 文件规格（分批编排，总计 2000 个）
| 批次 | 数量 | 单文件大小 |
| ---- | ---- | ---------- |
| 1    | 1000 | 10KB       |
| 2    | 500  | 20KB       |
| 3    | 300  | 100KB      |
| 4    | 200  | 200KB      |

## 测试目标（功能 + 性能双维度）
1. **功能正确性**: 每个文件传输后，校验文件大小 + MD5 hash（复用现有工具函数）
2. **性能指标**: 统计总耗时、平均单文件耗时、P95 耗时、各批次独立耗时、失败计数
3. **验收标准**: 
   - 2000 个文件传输成功率 100%
   - 上传总耗时 < 300 秒 (5 分钟)
   - 下载总耗时 < 300 秒 (5 分钟)

## 执行模式
- 第一版先实现**串行执行**（简单可靠，容易对比基准）
- 设计上预留并发扩展点（但暂不实现并发，因为 paramiko SFTP 线程不安全）

# 【约束 Constraints】
1. **不要并发**: paramiko SFTPClient 不是线程安全的，不要用 ThreadPoolExecutor 多线程共享同一个连接
2. **不要修改现有 fixture**: 新增的性能测试需要自己管理临时文件和连接
3. **临时文件清理**: 测试结束后必须清理所有本地和远程临时文件，不能污染测试数据目录
4. **不要硬编码路径**: 远程临时文件目录用 `/tmp/perf_test_XXXX` 随机命名，本地临时用 tempfile.mkdtemp()
5. **不要硬编码路径**: 测试用的文件都存放在`test_data_files`目录下, 这个目录中我又分为了2个目录, `source_data_files`和`destination_data_files`
   1. 做上传测试时, 在Windows本地对`source_data_files`目录生成2000个测试文件, 然后通过SFTP方式上传到WSL服务器对应`destination_data_files`目录下. `source_data_files`中的要被上传的文件命名pattern是`performance_test_to_upload_file_<yyyymmddhhmmss>_<number>`, `destination_data_files`中做下载到的测试文件命名pattern是被下载的那个文件的文件名中"to_upload"部分替换为"received".
   2. 做下载测试时, 在Windows本地对`source_data_files`目录生成2000个测试文件, 然后通过SFTP方式从WSL服务器下载到Windows本地的`destination_data_files`目录下. `source_data_files`中的要被下载的文件命名pattern是`performance_test_to_download_file_<yyyymmddhhmmss>_<number>`, `destination_data_files`中做下载收到的测试文件命名pattern是被下载的那个文件的文件名中"to_download"部分替换为"downloaded".

# 【输出要求 Output Format】
1. 测试文件放在 tests/ 目录下，命名为 test_performance_sftp_batch_transfer.py
2. 代码结构要求:
   - 一个 fixture 负责生成 2000 个临时测试文件（session scope）
   - 一个 fixture 负责远程临时目录的创建和清理
   - 一个 fixture 负责远程 SSH 连接（新建独立连接，不复用 sftp_client）
   - 两个测试函数: test_batch_upload_2000_files / test_batch_download_2000_files
   - 性能统计抽成独立的辅助函数
3. Allure 装饰器分级: feature="SFTP性能测试", story="批量文件传输", severity=CRITICAL

# 【元指令 Meta Instruction】
在输出代码之前，请先回答以下问题（用自然语言，不要用代码）：
1. 你打算怎么组织 2000 个文件的 fixture？是一次性生成还是分批生成？为什么？
2. 性能统计你打算用什么方式？P95 怎么计算？
3. 你有没有看到 paramiko SFTP 的线程安全风险？你的方案怎么规避？
4. Jenkins 上跑这个测试会不会超时？你有什么建议？

等我确认你的方案后，再输出完整代码。