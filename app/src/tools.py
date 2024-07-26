from pathlib import Path


def add_word_to_filename(path: Path, word: str = "processed"):
    dir_name = path.parent
    file_name = path.stem
    suffix = path.suffix
    return dir_name.joinpath(f"{file_name}_{word}{suffix}")
