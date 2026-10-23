import logging
from pathlib import Path

import paramiko
import pytest
from utils import local_file_md5, remote_file_md5

from constants import (
    UPLOAD_DESTINATION_FILE_PATH_WINDOWS,
    UPLOAD_DESTINATION_FILE_PATH_WSL,
    UPLOAD_SOURCE_FILE_PATH_WINDOWS,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_sftp_upload_file(
    sftp_client: paramiko.SFTPClient, ssh_client: paramiko.SSHClient
):
    # =================测试远程文件上传=================
    upload_source_file = UPLOAD_SOURCE_FILE_PATH_WINDOWS
    upload_target_file_wsl = UPLOAD_DESTINATION_FILE_PATH_WSL
    upload_target_file_windows = UPLOAD_DESTINATION_FILE_PATH_WINDOWS

    # 检查源文件是否存在, 如果不存在则生成一个10K大小的测试文件
    if not Path(upload_source_file).exists():
        with open(upload_source_file, "wb") as f:
            f.write(b"0" * 10240)

    sftp_client.put(upload_source_file, upload_target_file_wsl)
    logger.info(f"✅ 文件上传成功: {upload_source_file} -> {upload_target_file_wsl}")
    try:
        # 验证文件是否存在于远程服务器
        sftp_client.stat(upload_target_file_wsl)
    except OSError:
        raise AssertionError(
            f"文件上传后验证失败: 文件 {upload_target_file_wsl} 在远程服务器上不存在"
        )

    assert (
        Path(upload_target_file_windows).stat().st_size
        == Path(upload_source_file).stat().st_size
    ), f"文件 {upload_target_file_windows} 大小与源文件 {upload_source_file} 不一致"
    logger.info(
        f"✅ 已验证文件 {upload_target_file_wsl} 在远程服务器上存在, 且大小与源文件 {upload_source_file} 一致"
    )

    # 验证文件MD5值是否一致
    local_md5 = local_file_md5(upload_source_file)
    remote_md5 = remote_file_md5(ssh_client, upload_target_file_wsl)
    assert (
        local_md5 == remote_md5
    ), f"文件 {upload_target_file_wsl} 的MD5值与源文件 {upload_source_file} 不一致"
    logger.info(
        f"✅ 已验证文件 {upload_target_file_wsl} 的MD5值与源文件 {upload_source_file} 一致"
    )
