from pathlib import Path, PureWindowsPath


def windows_path_to_wsl(windows_path: str) -> str:
    p = PureWindowsPath(windows_path)
    drive = p.drive.rstrip(":").lower()
    body = str(p.relative_to(p.anchor)).replace("\\", "/")

    return f"/mnt/{drive}/{body}"


BASE_DIR = Path(__file__).parent

UPLOAD_SOURCE_FILE_PATH_WINDOWS = str(
    BASE_DIR / "test_data_files/source_data_files/nelson_temp_test_to_upload_file.txt"
)
UPLOAD_SOURCE_FILE_PATH_WSL = windows_path_to_wsl(UPLOAD_SOURCE_FILE_PATH_WINDOWS)

UPLOAD_DESTINATION_FILE_PATH_WINDOWS = str(
    BASE_DIR
    / "test_data_files/destination_data_files/nelson_temp_test_received_upload_file.txt"
)
UPLOAD_DESTINATION_FILE_PATH_WSL = windows_path_to_wsl(
    UPLOAD_DESTINATION_FILE_PATH_WINDOWS
)

DOWNLOAD_SOURCE_FILE_PATH_WINDOWS = str(
    BASE_DIR / "test_data_files/source_data_files/nelson_temp_test_to_download_file.txt"
)
DOWNLOAD_SOURCE_FILE_PATH_WSL = windows_path_to_wsl(DOWNLOAD_SOURCE_FILE_PATH_WINDOWS)

DOWNLOAD_TARGET_FILE_PATH_WINDOWS = str(
    BASE_DIR
    / "test_data_files/destination_data_files/nelson_temp_test_downloaded_file.txt"
)
DOWNLOAD_TARGET_FILE_PATH_WSL = windows_path_to_wsl(DOWNLOAD_TARGET_FILE_PATH_WINDOWS)


NONEXIST_PATH_WSL = "/tmp/this_path_should_never_exist_99999"

DESTINATION_FOLDER_PATH_WINDOWS = str(
    BASE_DIR / "test_data_files/destination_data_files"
)
