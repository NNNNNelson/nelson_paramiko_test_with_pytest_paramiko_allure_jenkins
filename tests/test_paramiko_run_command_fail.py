import logging

import paramiko
import pytest

from constants import NONEXIST_PATH_WSL

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_run_command_fail(ssh_client: paramiko.SSHClient):
    # =================测试远程命令执行=================
    test_nonexist_path = NONEXIST_PATH_WSL
    cmd = f"ls {test_nonexist_path}"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    ret_code = stdout.channel.recv_exit_status()
    logger.info(f"执行命令: {cmd}")
    logger.info(f"返回码 returncode = {ret_code}")
    logger.info(f"标准输出: {stdout.read().decode()}")
    logger.info(f"标准错误: {stderr.read().decode()}")
    assert ret_code != 0, f"路径 {test_nonexist_path} 不应该存在"

    # 测试assert失败是否会中断pipeline
    assert 1 == 2
