import pytest
from pathlib import Path
from geopandas import GeoDataFrame

# Import the necessary classes from your module
from src.io_vector import (FileReader,
                           GeoParquetHandler,
                           ShapefileHandler,
                           GeoJSONHandler,
                           KMLHandler)


from .conftest import TESTS_DIR, TESTS_DATA_DIR


@pytest.mark.parametrize("file_path, expected_handler", [
    ("data/file.parquet", GeoParquetHandler),
    ("data/file.shp", ShapefileHandler),
    ("data/file.geojson", GeoJSONHandler),
    ("data/file.kml", KMLHandler),
    (Path("data/file.parquet"), GeoParquetHandler),
    (Path("data/file.shp"), ShapefileHandler),
    (Path("data/file.geojson"), GeoJSONHandler),
    (Path("data/file.kml"), KMLHandler),
])
def test_get_handler(file_path, expected_handler):
    reader = FileReader(file_path)
    handler = reader._get_handler()
    assert isinstance(handler, expected_handler), f"Expected {expected_handler}, but got {type(handler)}"


def test_file_does_not_exist():
    file = Path("i_dont_exist.geopandas")

    with pytest.raises(FileNotFoundError):
        FileReader(file).read()


@pytest.mark.parametrize("file_path, handler_class", [
    (TESTS_DATA_DIR.joinpath("ARG.geojson"), GeoJSONHandler),
])
def test_read(file_path, handler_class, mocker):
    # Mock the read methods to avoid actual file I/O
    mocker.patch.object(handler_class, 'read', return_value=GeoDataFrame())

    reader = FileReader(file_path)
    data = reader.read()

    assert isinstance(data, GeoDataFrame), "Data should be a GeoDataFrame"


def test_raise_unknown_file_format():

    unknown_file_fmt = TESTS_DATA_DIR.joinpath("data.nc")
    reader = FileReader(unknown_file_fmt)

    with pytest.raises(ValueError):
        reader.read()
