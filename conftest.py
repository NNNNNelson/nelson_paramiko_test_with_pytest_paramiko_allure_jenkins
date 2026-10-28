import hashlib
import json
import logging
import os
import re
import time
import uuid as _uuid
from collections.abc import Iterator
from pathlib import Path
import platform
import sys

import paramiko
import pytest
from dotenv import load_dotenv

from constants import DESTINATION_FOLDER_PATH_WINDOWS

load_dotenv()
logger = logging.getLogger(__name__)


HOST = os.getenv("SSH_HOST", "127.0.0.1")
USER = os.getenv("SSH_USER")
PWD = os.getenv("SSH_PWD")

if not USER or not PWD:
    pytest.exit("❌ 环境变量 SSH_USER/SSH_PWD 未配置, 请检查 .env 文件")


@pytest.fixture(scope="session")
def ssh_client() -> Iterator[paramiko.SSHClient]:
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                HOST, username=USER, password=PWD, timeout=10, banner_timeout=10
            )
        except paramiko.AuthenticationException:
            logger.error("❌ 认证失败, 请检查用户名/密码")
            raise
        except paramiko.SSHException as e:
            logger.error(f"❌ ssh连接异常: {e}")
            raise
        logger.info("✅ ssh连接成功")
        yield ssh
    logger.info("🔌 ssh连接已断开")


@pytest.fixture(scope="session")
def sftp_client(ssh_client: paramiko.SSHClient) -> Iterator[paramiko.SFTPClient]:
    with ssh_client.open_sftp() as sftp:
        yield sftp
    logger.info("🔌 sftp连接已断开")


@pytest.fixture(scope="session", autouse=True)
def clean_up_test_files():
    destination_folder_path = DESTINATION_FOLDER_PATH_WINDOWS
    os.makedirs(destination_folder_path, exist_ok=True)
    for entry in os.scandir(destination_folder_path):
        if entry.is_file():
            os.remove(entry.path)
            logger.info(f"🧹 已删除旧测试文件 {entry.path}")


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    yield

    alluredir = session.config.getoption("alluredir", default="allure-results")
    allure_dir = Path(alluredir)
    allure_dir.mkdir(parents=True, exist_ok=True)

    env_content = [
        f"Python.version={sys.version.split()[0]}",
        f"OS={platform.system()}",
        f"OS.Version={platform.release()}",
        f"OS.Architecture={platform.machine()}",
        f"SSH.Host={HOST}",
        f"SSH.User={USER}",
        f"Pytest.Version={pytest.__version__}",
        f"Paramiko.Version={paramiko.__version__}",
        f"Alluredir={str(allure_dir.resolve()).replace(os.sep, "/")}",
    ]
    env_path = allure_dir / "environment.properties"
    env_path.write_text("\n".join(env_content) + "\n", encoding="utf-8")
    logger.info(f"📝 Allure environment.properties 已写入 → {env_path}")

    categories = [
        {
            "name": "Product Defects",
            "matchedStatuses": ["broken"],
        },
        {
            "name": "Test Defects",
            "matchedStatuses": ["failed"],
        },
        {
            "name": "Flaky Tests",
            "matchedStatuses": ["broken", "failed"],
            "flaky": True,
        },
    ]
    cat_path = allure_dir / "categories.json"
    cat_path.write_text(
        json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"📝 Allure categories.json 已写入 → {cat_path}")

    # --------------------------------------------------------------
    # 为因 --maxfail / session.shouldstop 而未执行的测试
    # 生成 skipped 状态的 Allure result.json
    # 否则 Allure History Trend 会把它们显示成 "继承上一次的状态"
    # （比如上一次 passed，这一次没跑也被画成绿色 → 假阳性）
    # --------------------------------------------------------------
    _fill_skipped_for_unexecuted(allure_dir, session)


def _nodeid_to_allure_fullname(nodeid: str) -> str:
    """把 pytest nodeid 转成 allure-pytest 使用的 fullName 格式。

    转换规则:
      tests/test_foo.py::test_bar  →  tests.test_foo#test_bar
      tests/sub/test_x.py::test_y →  tests.sub.test_x#test_y
    """
    # /  →  .
    fullname = nodeid.replace("/", ".")
    # .py::  →  #
    fullname = re.sub(r"\.py::", "#", fullname)
    # 兜底: 没 .py 的参数化节点也用 :: → #
    fullname = fullname.replace("::", "#")
    return fullname


def _fill_skipped_for_unexecuted(allure_dir: Path, session):
    """扫描 session.items，为每个没有 result.json 的已收集测试生成 skipped 记录。"""

    # =====================================================================
    # DEBUG V3: 直接 print 到 stdout, 绕过 logger 配置
    # =====================================================================
    print("\n" + "=" * 70, flush=True)
    print("  DEBUG_V3 _fill_skipped_for_unexecuted START", flush=True)
    print("=" * 70, flush=True)
    print(f"  allure_dir = {allure_dir}", flush=True)
    print(f"  allure_dir.resolve() = {allure_dir.resolve()}", flush=True)
    print(f"  allure_dir.exists() = {allure_dir.exists()}", flush=True)
    print(f"  len(session.items) = {len(session.items)}", flush=True)

    # 列出 allure_dir 里的所有文件（包括子目录）
    print(f"\n  📁 allure_dir 全部内容:", flush=True)
    for p in sorted(allure_dir.rglob("*")) if allure_dir.exists() else []:
        print(f"    {p.relative_to(allure_dir)}", flush=True)

    # 1. 收集 allure-results 里已有 result.json 的 fullName 集合
    executed_fullnames: set[str] = set()
    print(f"\n  🔍 glob('*-result.json') 匹配到:", flush=True)
    for rf in allure_dir.glob("*-result.json"):
        print(f"    📄 {rf.name}", flush=True)
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            if "fullName" in data:
                print(f"       → fullName={data['fullName']}, status={data.get('status','?')}", flush=True)
                executed_fullnames.add(data["fullName"])
            else:
                print(f"       → ⚠️ 无 fullName 字段!", flush=True)
        except (json.JSONDecodeError, OSError) as e:
            print(f"       → ❌ 读取失败: {e}", flush=True)

    print(f"\n  ✅ executed_fullnames ({len(executed_fullnames)} 个):", flush=True)
    for fn in sorted(executed_fullnames):
        print(f"    {fn}", flush=True)

    # 2. 遍历所有被收集的测试项，找出没执行的
    skipped_count = 0
    now_ms = int(time.time() * 1000)

    print(f"\n  🔁 遍历 session.items:", flush=True)
    for item in session.items:
        fullname = _nodeid_to_allure_fullname(item.nodeid)
        is_in = fullname in executed_fullnames
        print(f"    {'✅' if is_in else '❌'} nodeid={item.nodeid}", flush=True)
        print(f"       → fullName={fullname}, 已执行={is_in}", flush=True)

        if is_in:
            continue  # 已经有 result.json 了（passed/failed/skipped 都是）

        # 3. 组装 labels（复制 pytest markers，作为 Allure tag）
        labels: list[dict] = []
        for marker in item.iter_markers():
            labels.append({"name": "tag", "value": marker.name})

        # 4. 组装 titlePath（和 allure-pytest 保持一致: ["tests", "module.py"]）
        title_path: list[str] = []
        try:
            module_part = item.nodeid.split("::")[0]
            title_path = module_part.split("/")
        except Exception:
            title_path = []

        # 5. historyId / testCaseId = md5(fullName)
        hashed = hashlib.md5(fullname.encode("utf-8")).hexdigest()

        result = {
            "uuid": str(_uuid.uuid4()),
            "historyId": hashed,
            "testCaseId": hashed,
            "fullName": fullname,
            "name": item.name,
            "status": "skipped",
            "start": now_ms,
            "stop": now_ms,
            "labels": labels,
            "titlePath": title_path,
            "message": "Skipped by pytest due to --maxfail or early session stop",
        }

        out_file = allure_dir / f"{result['uuid']}-result.json"
        out_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        skipped_count += 1
        print(f"       ⏭️  已写入 skipped result.json → {out_file.name}", flush=True)
        logger.info(f"⏭️  未执行测试补全为 skipped → {fullname}")

    print(f"\n  📊 总结: skipped_count={skipped_count}", flush=True)
    print("=" * 70 + "\n", flush=True)

    if skipped_count > 0:
        logger.info(
            f"📝 Allure: 共 {skipped_count} 个未执行测试已补全为 skipped 状态"
        )
