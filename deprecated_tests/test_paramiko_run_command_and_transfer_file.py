import logging
from pathlib import Path

import paramiko

from constants import (
    DOWNLOAD_SOURCE_FILE_PATH,
    DOWNLOAD_TARGET_FILE_PATH,
    NONEXIST_PATH,
    UPLOAD_DESTINATION_FILE_PATH,
    UPLOAD_SOURCE_FILE_PATH_WSL,
    UPLOAD_SOURCE_FILE_PATH_WINDOWS,
)

logger = logging.getLogger(__name__)


def test_run_command(ssh_client: paramiko.SSHClient):
    # =================测试远程命令执行=================
    test_file_path = UPLOAD_SOURCE_FILE_PATH_WSL
    cmd = f"ls {test_file_path}"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    ret_code = stdout.channel.recv_exit_status()
    logger.info(f"执行命令: {cmd}")
    logger.info(f"返回码 returncode = {ret_code}")
    logger.info(f"标准输出: {stdout.read().decode()}")
    logger.info(f"标准错误: {stderr.read().decode()}")
    assert ret_code == 0, f"文件 {test_file_path} 不存在"

    # =================测试远程命令执行=================
    test_nonexist_path = NONEXIST_PATH
    cmd = f"ls {test_nonexist_path}"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    ret_code = stdout.channel.recv_exit_status()
    logger.info(f"执行命令: {cmd}")
    logger.info(f"返回码 returncode = {ret_code}")
    logger.info(f"标准输出: {stdout.read().decode()}")
    logger.info(f"标准错误: {stderr.read().decode()}")
    assert ret_code != 0, f"路径 {test_nonexist_path} 不应该存在"


def test_transfer_file(sftp_client: paramiko.SFTPClient):
    # =================测试远程文件上传=================
    upload_source_file = UPLOAD_SOURCE_FILE_PATH_WINDOWS
    upload_target_file = UPLOAD_DESTINATION_FILE_PATH
    sftp_client.put(upload_source_file, upload_target_file)
    logger.info(f"✅ 文件上传成功: {upload_source_file} -> {upload_target_file}")
    try:
        sftp_client.stat(upload_target_file)
    except FileNotFoundError:
        raise AssertionError(
            f"文件上传后验证失败: 文件 {upload_target_file} 在远程服务器上不存在"
        )
    logger.info(f"✅ 已验证文件 {upload_target_file} 在远程服务器上存在")

    # =================测试远程文件下载=================
    download_source_file = DOWNLOAD_SOURCE_FILE_PATH
    download_target_file = DOWNLOAD_TARGET_FILE_PATH
    sftp_client.get(download_source_file, download_target_file)
    logger.info(f"✅ 文件下载成功: {download_source_file} -> {download_target_file}")
    assert (
        Path(download_target_file).exists() and Path(download_target_file).is_file()
    ), f"文件 {download_target_file} 在本地服务器上不存在"
    logger.info(f"✅ 已验证文件 {download_target_file} 在本地服务器上存在")
