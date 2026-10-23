from pathlib import Path

BASE_DIR = Path(__file__).parent
UPLOAD_SOURCE_FILE_PATH_WSL = "/mnt/i/nelson_private_projects/nelson_temp_test_workspace/test_data_files/source_data_files/nelson_temp_test_to_upload_file.txt"
UPLOAD_SOURCE_FILE_PATH_WINDOWS = str(
    BASE_DIR / "test_data_files/source_data_files/nelson_temp_test_to_upload_file.txt"
)
UPLOAD_DESTINATION_FILE_PATH_WSL = "/mnt/i/nelson_private_projects/nelson_temp_test_workspace/test_data_files/destination_data_files/nelson_temp_test_received_upload_file.txt"
UPLOAD_DESTINATION_FILE_PATH_WINDOWS = str(
    BASE_DIR
    / "test_data_files/destination_data_files/nelson_temp_test_received_upload_file.txt"
)
DOWNLOAD_SOURCE_FILE_PATH_WSL = "/mnt/i/nelson_private_projects/nelson_temp_test_workspace/test_data_files/source_data_files/nelson_temp_test_to_download_file.txt"
DOWNLOAD_SOURCE_FILE_PATH_WINDOWS = str(
    BASE_DIR / "test_data_files/source_data_files/nelson_temp_test_to_download_file.txt"
)
DOWNLOAD_TARGET_FILE_PATH_WINDOWS = str(
    BASE_DIR
    / "test_data_files/destination_data_files/nelson_temp_test_downloaded_file.txt"
)
NONEXIST_PATH_WSL = "/tmp/this_path_should_never_exist_99999"
DESTINATION_FOLDER_PATH_WINDOWS = str(
    BASE_DIR / "test_data_files/destination_data_files"
)
