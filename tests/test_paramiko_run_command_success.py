import logging

import allure
import paramiko
import pytest

from constants import UPLOAD_SOURCE_FILE_PATH_WSL

logger = logging.getLogger(__name__)


@pytest.mark.smoke
@pytest.mark.integration
@allure.feature("SSH远程命令")
@allure.story("命令执行成功")
@allure.title("验证远程文件存在的命令执行成功")
def test_run_command_success(ssh_client: paramiko.SSHClient):
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
