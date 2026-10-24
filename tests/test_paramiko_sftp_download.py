import logging
from pathlib import Path

import allure
import paramiko
import pytest

from constants import (
    DOWNLOAD_SOURCE_FILE_PATH_WINDOWS,
    DOWNLOAD_SOURCE_FILE_PATH_WSL,
    DOWNLOAD_TARGET_FILE_PATH_WINDOWS,
)
from utils import local_file_md5, remote_file_md5

logger = logging.getLogger(__name__)


@allure.feature("SFTP文件传输")
@allure.story("文件下载")
@allure.title("从远程 WSL 下载文件到本地 Windows 并验证 MD5")
@pytest.mark.integration
def test_sftp_download_file(
    sftp_client: paramiko.SFTPClient, ssh_client: paramiko.SSHClient
):
    # =================测试远程文件下载=================
    download_source_file_windows = DOWNLOAD_SOURCE_FILE_PATH_WINDOWS
    download_source_file_wsl = DOWNLOAD_SOURCE_FILE_PATH_WSL
    download_target_file = DOWNLOAD_TARGET_FILE_PATH_WINDOWS

    # 检查源文件是否存在, 如果不存在则生成一个10K大小的测试文件
    if not Path(download_source_file_windows).exists():
        with open(download_source_file_windows, "wb") as f:
            f.write(b"0" * 10240)

    sftp_client.get(download_source_file_wsl, download_target_file)
    logger.info(
        f"✅ 文件下载成功: {download_source_file_wsl} -> {download_target_file}"
    )
    assert (
        Path(download_target_file).exists() and Path(download_target_file).is_file()
    ), f"文件 {download_target_file} 在本地服务器上不存在"

    assert (
        Path(download_target_file).stat().st_size
        == Path(download_source_file_windows).stat().st_size
    ), f"文件 {download_target_file} 大小与源文件 {download_source_file_windows} 不一致"
    logger.info(
        f"✅ 已验证文件 {download_target_file} 在本地服务器上存在, 且大小与源文件 {download_source_file_windows} 一致"
    )

    remote_md5 = remote_file_md5(ssh_client, download_source_file_wsl)
    local_md5 = local_file_md5(download_target_file)
    assert (
        remote_md5 == local_md5
    ), f"远程文件 {download_source_file_wsl} 与本地文件 {download_target_file} 的MD5值不一致"
    logger.info(
        f"✅ 已验证本地文件 {download_target_file} 的MD5值与远程文件 {download_source_file_wsl} 一致"
    )
