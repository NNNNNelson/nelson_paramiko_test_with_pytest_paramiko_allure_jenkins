"""
SFTP 批量文件传输性能测试
==========================
- 串行执行 2000 个文件的上传 / 下载，规避 paramiko SFTPClient 线程安全问题
- 统计总耗时、平均单文件耗时、P95 耗时、各批次独立耗时、失败计数
- 临时文件与远程目录均在 fixture 清理阶段回收，不污染测试数据目录
"""

import logging
import os
import random
import string
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import allure
import paramiko
import pytest

from constants import (
    DESTINATION_DATA_FILES_DIR_WINDOWS,
    SOURCE_DATA_FILES_DIR_WINDOWS,
    SOURCE_DATA_FILES_DIR_WSL,
)
from utils import local_file_md5, remote_file_md5

logger = logging.getLogger(__name__)

# Allure 附件类型兼容层：allure-commons 在较新版本才引入 MARKDOWN 枚举，
# 旧版本（含本项目 pyproject.toml 指定的 allure-pytest>=2.16.2）只有 TEXT。
# Allure 会自动识别 Markdown 格式的 TEXT 附件并正常渲染，所以 fallback 到 TEXT 即可。
_ALLURE_MD_ATTACHMENT_TYPE = getattr(
    allure.attachment_type, "MARKDOWN", allure.attachment_type.TEXT
)

# ---------------------------------------------------------------------------
# 测试规格常量（直接来自需求 Spec）
# ---------------------------------------------------------------------------
BATCH_SPECS: list[dict] = [
    {"batch_idx": 1, "count": 1000, "size_kb": 10},
    {"batch_idx": 2, "count": 500, "size_kb": 20},
    {"batch_idx": 3, "count": 300, "size_kb": 100},
    {"batch_idx": 4, "count": 200, "size_kb": 200},
]
TOTAL_FILE_COUNT = sum(spec["count"] for spec in BATCH_SPECS)
ACCEPTANCE_MAX_TOTAL_SECONDS = 300  # 5 分钟

# 从环境变量读取 SSH 连接信息（与 conftest.py 保持一致）
_HOST = os.getenv("SSH_HOST", "127.0.0.1")
_USER = os.getenv("SSH_USER")
_PWD = os.getenv("SSH_PWD")


# ===========================================================================
# 性能统计辅助函数
# ===========================================================================


def _compute_percentile(sorted_durations: list[float], p: float) -> float:
    """
    计算百分位数（如 P95）。
    :param sorted_durations: 已升序排列的耗时列表（秒）
    :param p: 百分位值，范围 (0, 100]
    """
    if not sorted_durations:
        return 0.0
    # 边界处理：单元素直接返回
    if len(sorted_durations) == 1:
        return sorted_durations[0]
    # 整数索引法，确保至少取到最后一个元素
    idx = int(len(sorted_durations) * p / 100)
    if idx >= len(sorted_durations):
        idx = len(sorted_durations) - 1
    return sorted_durations[idx]


def _build_batch_stats_row(
    batch_idx: int,
    size_kb: int,
    durations: list[float],
    failures: int,
) -> str:
    """构建单个批次的统计表格行。"""
    if not durations:
        return f"| {batch_idx} | {size_kb}KB | 0 | 0.00s |   -   |   -   |   -   | 0 |"
    sorted_durs = sorted(durations)
    total = sum(durations)
    avg = total / len(durations)
    p95 = _compute_percentile(sorted_durs, 95)
    max_d = sorted_durs[-1]
    return (
        f"| {batch_idx} | {size_kb}KB | {len(durations)} | {total:6.2f}s | "
        f"{avg:6.3f}s | {p95:6.3f}s | {max_d:6.3f}s | {failures} |"
    )


def _build_total_stats_row(
    durations: list[float],
    failures: int,
    label: str = "合计",
) -> str:
    """构建总计行。"""
    if not durations:
        return f"| {label} |   -   | 0 | 0.00s |   -   |   -   |   -   | {failures} |"
    sorted_durs = sorted(durations)
    total = sum(durations)
    avg = total / len(durations)
    p95 = _compute_percentile(sorted_durs, 95)
    max_d = sorted_durs[-1]
    return (
        f"| {label} |   -   | {len(durations)} | {total:6.2f}s | "
        f"{avg:6.3f}s | {p95:6.3f}s | {max_d:6.3f}s | {failures} |"
    )


def _format_stats_summary(
    label: str,
    batch_results: list[dict],
    all_durations: list[float],
    total_failures: int,
) -> str:
    """
    生成完整的性能统计 Markdown 表格，用于 Allure attach 和日志输出。
    """
    sep = (
        "| batch | size  | count | total  |  avg   |  P95   |  max   | fail |\n"
        "|-------|-------|-------|--------|--------|--------|--------|------|"
    )
    rows = "\n".join(
        _build_batch_stats_row(
            br["batch_idx"], br["size_kb"], br["durations"], br["failures"]
        )
        for br in batch_results
    )
    total_row = _build_total_stats_row(all_durations, total_failures)
    success_rate = (
        (TOTAL_FILE_COUNT - total_failures) / TOTAL_FILE_COUNT * 100
        if TOTAL_FILE_COUNT
        else 0.0
    )
    summary = (
        f"## {label}\n\n"
        f"- **总文件数**: {TOTAL_FILE_COUNT}\n"
        f"- **成功数**: {TOTAL_FILE_COUNT - total_failures}\n"
        f"- **失败数**: {total_failures}\n"
        f"- **成功率**: {success_rate:.2f}%\n\n"
        f"{sep}\n{rows}\n{total_row}"
    )
    return summary


def _build_local_file_path(prefix: str, seq: int) -> Path:
    """
    构建 source_data_files 中的文件路径。
    :param prefix: 'to_upload' 或 'to_download'
    :param seq:    序号（zero-pad 到 4 位，保证字典序正确）
    :return: Path 对象，文件名形如 performance_test_to_upload_file_20261026120000_0001
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"performance_test_{prefix}_file_{ts}_{seq:04d}"
    return Path(SOURCE_DATA_FILES_DIR_WINDOWS) / file_name


def _remote_temp_dir_name() -> str:
    """生成随机远程临时目录名，形如 perf_test_20261026120000_a1b2c3."""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"/tmp/perf_test_{ts}_{suffix}"


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="session")
def perf_ssh_connection() -> Iterator[paramiko.SSHClient]:
    """
    新建独立 SSH / SFTP 连接（session 级）。
    不复用 conftest.py 中的 ssh_client 单例，保持连接隔离。
    超时参数比 conftest 宽松（30s vs 10s），适配 Jenkins CI 环境。
    """
    if not _USER or not _PWD:
        pytest.exit("❌ 性能测试需要 SSH_USER / SSH_PWD 环境变量")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            _HOST,
            username=_USER,
            password=_PWD,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        logger.info("✅ [perf] 独立 SSH 连接成功")
    except Exception as exc:
        logger.error(f"❌ [perf] SSH 连接失败: {exc}")
        raise

    yield ssh

    ssh.close()
    logger.info("🔌 [perf] 独立 SSH 连接已关闭")


@pytest.fixture(scope="session")
def remote_perf_dir(perf_ssh_connection: paramiko.SSHClient) -> Iterator[str]:
    """
    在远程 WSL 上创建唯一的临时目录（/tmp/perf_test_XXXX），
    yield 返回完整路径，session 结束后 rm -rf 清理。
    """
    remote_dir = _remote_temp_dir_name()
    _, stdout, stderr = perf_ssh_connection.exec_command(f"mkdir -p {remote_dir}")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        raise RuntimeError(f"❌ [perf] 创建远程目录失败: {stderr.read().decode()}")
    logger.info(f"📁 [perf] 远程临时目录已创建: {remote_dir}")

    yield remote_dir

    # --- 清理阶段 ---
    _, stdout, stderr = perf_ssh_connection.exec_command(f"rm -rf {remote_dir}")
    stdout.channel.recv_exit_status()
    logger.info(f"🧹 [perf] 远程临时目录已清理: {remote_dir}")


def _generate_batch_files(
    prefix: str,
) -> tuple[list[dict], list[Path]]:
    """
    按批次在 source_data_files 目录生成 2000 个测试文件。
    :param prefix: 'to_upload' 或 'to_download'
    :return: (批次列表, 所有生成文件的 Path 列表)
             每个批次 dict 结构: {batch_idx, size_kb, files: List[Path]}
    """
    os.makedirs(SOURCE_DATA_FILES_DIR_WINDOWS, exist_ok=True)
    all_files: list[Path] = []
    batches: list[dict] = []
    seq = 1

    for spec in BATCH_SPECS:
        batch_files: list[Path] = []
        size_bytes = spec["size_kb"] * 1024
        # 用固定大小的 b"0" 填充，与现有测试风格保持一致
        chunk = b"0" * 65536  # 64KB 分块，避免大文件一次性占内存
        for _ in range(spec["count"]):
            file_path = _build_local_file_path(prefix, seq)
            remaining = size_bytes
            with open(file_path, "wb") as f:
                while remaining > 0:
                    write_size = min(len(chunk), remaining)
                    f.write(chunk[:write_size])
                    remaining -= write_size
            batch_files.append(file_path)
            all_files.append(file_path)
            seq += 1
        batches.append(
            {
                "batch_idx": spec["batch_idx"],
                "size_kb": spec["size_kb"],
                "count": spec["count"],
                "files": batch_files,
            }
        )
        logger.info(
            f"📦 [perf] 批次 {spec['batch_idx']} 生成完成: "
            f"{spec['count']} 个 x {spec['size_kb']}KB"
        )

    logger.info(f"📦 [perf] 全部 {len(all_files)} 个测试文件已就绪")
    return batches, all_files


@pytest.fixture(scope="session")
def upload_test_files() -> Iterator[list[dict]]:
    """生成 2000 个上传测试文件（prefix='to_upload'），yield 后清理。"""
    batches, all_files = _generate_batch_files("to_upload")
    yield batches

    # --- 清理 source 文件 ---
    for f in all_files:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass
    logger.info(f"🧹 [perf] 已清理 {len(all_files)} 个上传源文件")


@pytest.fixture(scope="session")
def download_test_files() -> Iterator[list[dict]]:
    """生成 2000 个下载测试文件（prefix='to_download'），yield 后清理。"""
    batches, all_source_files = _generate_batch_files("to_download")

    # yield 前先确保 destination_data_files 里没有已有的 downloaded 文件
    dest_dir = Path(DESTINATION_DATA_FILES_DIR_WINDOWS)
    if dest_dir.exists():
        for existing in dest_dir.glob("performance_test_downloaded_file_*"):
            try:
                existing.unlink()
            except Exception:
                pass

    yield batches

    # --- 清理 source 文件 ---
    for f in all_source_files:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass
    logger.info(f"🧹 [perf] 已清理 {len(all_source_files)} 个下载源文件")

    # --- 清理 destination 目录中的 downloaded 文件 ---
    if dest_dir.exists():
        removed = 0
        for f in dest_dir.glob("performance_test_downloaded_file_*"):
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
        logger.info(f"🧹 [perf] 已清理 destination 目录中 {removed} 个下载文件")


def _dest_name_for_download(src_name: str) -> str:
    """下载测试中，本地 destination 文件名：'to_download' → 'downloaded'."""
    return src_name.replace("to_download", "downloaded")


# ===========================================================================
# 测试用例
# ===========================================================================


@allure.feature("SFTP性能测试")
@allure.story("批量文件上传")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(f"串行上传 {TOTAL_FILE_COUNT} 个文件并校验 MD5")
@allure.description(
    f"按 4 个批次串行上传共 {TOTAL_FILE_COUNT} 个文件（10KB~200KB），"
    f"统计总耗时、平均耗时、P95、各批次独立耗时及失败计数。"
)
@pytest.mark.perf
def test_batch_upload_2000_files(
    perf_ssh_connection: paramiko.SSHClient,
    remote_perf_dir: str,
    upload_test_files: list[dict],
):
    """串行上传 2000 个文件到远程临时目录并校验 MD5 + 性能指标。"""

    batch_results: list[dict] = []
    all_durations: list[float] = []
    total_failures = 0
    total_start = time.perf_counter()

    sftp = perf_ssh_connection.open_sftp()
    try:
        for batch in upload_test_files:
            batch_durations: list[float] = []
            batch_failures = 0

            for local_path in batch["files"]:
                remote_path = f"{remote_perf_dir}/{local_path.name}"
                file_start = time.perf_counter()
                try:
                    # --- SFTP put ---
                    sftp.put(str(local_path), remote_path)
                    file_elapsed = time.perf_counter() - file_start
                    batch_durations.append(file_elapsed)
                    all_durations.append(file_elapsed)

                    # --- 校验：文件大小 + MD5 ---
                    remote_info = sftp.stat(remote_path)
                    local_size = local_path.stat().st_size
                    assert (
                        remote_info.st_size == local_size
                    ), f"大小不一致: {remote_path} (远程 {remote_info.st_size} vs 本地 {local_size})"

                    local_md5 = local_file_md5(str(local_path))
                    remote_md5 = remote_file_md5(perf_ssh_connection, remote_path)
                    assert (
                        local_md5 == remote_md5
                    ), f"MD5 不一致: {local_path} ({local_md5} != {remote_md5})"

                except Exception as exc:
                    batch_failures += 1
                    total_failures += 1
                    logger.error(f"❌ 上传失败 {local_path.name}: {exc}")

            batch_results.append(
                {
                    "batch_idx": batch["batch_idx"],
                    "size_kb": batch["size_kb"],
                    "durations": batch_durations,
                    "failures": batch_failures,
                }
            )
            logger.info(
                f"  ✅ 批次 {batch['batch_idx']} ({batch['size_kb']}KB x {batch['count']}): "
                f"成功 {len(batch_durations)}, 失败 {batch_failures}"
            )

    finally:
        sftp.close()

    total_elapsed = time.perf_counter() - total_start

    # --- 构建统计摘要 ---
    stats = _format_stats_summary(
        label=f"批量上传性能测试（总耗时 {total_elapsed:.2f}s）",
        batch_results=batch_results,
        all_durations=all_durations,
        total_failures=total_failures,
    )

    # --- 输出日志 ---
    logger.info("\n" + stats)

    # --- 附加到 Allure 报告 ---
    allure.attach(
        stats,
        name="上传性能统计",
        attachment_type=_ALLURE_MD_ATTACHMENT_TYPE,
    )

    # --- 验收断言 ---
    success_rate = (TOTAL_FILE_COUNT - total_failures) / TOTAL_FILE_COUNT * 100
    assert (
        total_failures == 0
    ), f"❌ 上传失败 {total_failures} 个，成功率 {success_rate:.2f}%，未达 100%"
    assert total_elapsed < ACCEPTANCE_MAX_TOTAL_SECONDS, (
        f"❌ 上传总耗时 {total_elapsed:.2f}s 超过验收标准 "
        f"{ACCEPTANCE_MAX_TOTAL_SECONDS}s"
    )
    logger.info(
        f"🎉 上传测试通过: 成功率 {success_rate:.2f}%, 总耗时 {total_elapsed:.2f}s"
    )


@allure.feature("SFTP性能测试")
@allure.story("批量文件下载")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title(f"串行下载 {TOTAL_FILE_COUNT} 个文件并校验 MD5")
@allure.description(
    f"按 4 个批次串行从 WSL（通过 /mnt 挂载）下载共 {TOTAL_FILE_COUNT} 个文件"
    f"到本地 destination_data_files，统计总耗时、平均耗时、P95、各批次独立耗时及失败计数。"
)
@pytest.mark.perf
def test_batch_download_2000_files(
    perf_ssh_connection: paramiko.SSHClient,
    download_test_files: list[dict],
):
    """串行下载 2000 个文件到本地 destination 目录并校验 MD5 + 性能指标。"""

    batch_results: list[dict] = []
    all_durations: list[float] = []
    total_failures = 0
    total_start = time.perf_counter()

    dest_dir = Path(DESTINATION_DATA_FILES_DIR_WINDOWS)
    os.makedirs(dest_dir, exist_ok=True)

    sftp = perf_ssh_connection.open_sftp()
    try:
        for batch in download_test_files:
            batch_durations: list[float] = []
            batch_failures = 0

            for local_source in batch["files"]:
                # WSL 通过 /mnt 挂载直接看到 Windows 文件系统
                remote_source_path = f"{SOURCE_DATA_FILES_DIR_WSL}/{local_source.name}"
                dest_file_name = _dest_name_for_download(local_source.name)
                local_dest_path = dest_dir / dest_file_name

                file_start = time.perf_counter()
                try:
                    # --- SFTP get ---
                    sftp.get(remote_source_path, str(local_dest_path))
                    file_elapsed = time.perf_counter() - file_start
                    batch_durations.append(file_elapsed)
                    all_durations.append(file_elapsed)

                    # --- 校验：文件大小 + MD5 ---
                    source_size = local_source.stat().st_size
                    dest_size = local_dest_path.stat().st_size
                    assert (
                        source_size == dest_size
                    ), f"大小不一致: {local_dest_path} (源 {source_size} vs 目标 {dest_size})"

                    source_md5 = local_file_md5(str(local_source))
                    dest_md5 = local_file_md5(str(local_dest_path))
                    assert (
                        source_md5 == dest_md5
                    ), f"MD5 不一致: {local_dest_path} ({source_md5} != {dest_md5})"

                except Exception as exc:
                    batch_failures += 1
                    total_failures += 1
                    logger.error(f"❌ 下载失败 {local_source.name}: {exc}")

            batch_results.append(
                {
                    "batch_idx": batch["batch_idx"],
                    "size_kb": batch["size_kb"],
                    "durations": batch_durations,
                    "failures": batch_failures,
                }
            )
            logger.info(
                f"  ✅ 批次 {batch['batch_idx']} ({batch['size_kb']}KB x {batch['count']}): "
                f"成功 {len(batch_durations)}, 失败 {batch_failures}"
            )

    finally:
        sftp.close()

    total_elapsed = time.perf_counter() - total_start

    # --- 构建统计摘要 ---
    stats = _format_stats_summary(
        label=f"批量下载性能测试（总耗时 {total_elapsed:.2f}s）",
        batch_results=batch_results,
        all_durations=all_durations,
        total_failures=total_failures,
    )

    # --- 输出日志 ---
    logger.info("\n" + stats)

    # --- 附加到 Allure 报告 ---
    allure.attach(
        stats,
        name="下载性能统计",
        attachment_type=_ALLURE_MD_ATTACHMENT_TYPE,
    )

    # --- 验收断言 ---
    success_rate = (TOTAL_FILE_COUNT - total_failures) / TOTAL_FILE_COUNT * 100
    assert (
        total_failures == 0
    ), f"❌ 下载失败 {total_failures} 个，成功率 {success_rate:.2f}%，未达 100%"
    assert total_elapsed < ACCEPTANCE_MAX_TOTAL_SECONDS, (
        f"❌ 下载总耗时 {total_elapsed:.2f}s 超过验收标准 "
        f"{ACCEPTANCE_MAX_TOTAL_SECONDS}s"
    )
    logger.info(
        f"🎉 下载测试通过: 成功率 {success_rate:.2f}%, 总耗时 {total_elapsed:.2f}s"
    )
