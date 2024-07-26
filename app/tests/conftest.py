from pathlib import Path

TESTS_DIR = current_file_path = Path(__file__).parent.resolve()
TESTS_DATA_DIR = TESTS_DIR.joinpath("data")
