import json
import logging
import os
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
        f"Alluredir={allure_dir.resolve()}",
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
