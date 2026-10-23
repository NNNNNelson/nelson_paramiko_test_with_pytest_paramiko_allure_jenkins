import hashlib

import paramiko


def local_file_md5(file_path: str) -> str:
    """分块计算本地文件的MD5, 避免大文件一次性读入内存."""
    block_size = 65536
    md5 = hashlib.md5()

    with open(file_path, "rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def remote_file_md5(ssh: paramiko.SSHClient, remote_path: str) -> str:
    """通过执行 md5sum 命令获取远程文件的 MD5 值."""
    cmd = f"md5sum {remote_path}"
    _, stdout, stderr = ssh.exec_command(cmd)
    ret_code = stdout.channel.recv_exit_status()
    if ret_code != 0:
        raise RuntimeError(f"远程 md5sum 执行失败: {stderr.read().decode()}")
    return stdout.read().decode().split()[0]  # 提取MD5值, 忽略文件名
