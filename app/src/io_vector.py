
"""
Handle all these file formats: GeoParquet, ESRI Shapefile, GeoJSON, KML
"""

from abc import ABC, abstractmethod
import geopandas as gpd
from fastkml import kml
from shapely.geometry import shape
from typing import Union, Type
from pathlib import Path

from src.logging_config import logger


class GeoDataHandler(ABC):
    def __init__(self, file_path: Path):
        self._data = None
        self.file_path = file_path

    @property
    def data(self) -> Union[gpd.GeoDataFrame, None]:
        return self._data

    @data.setter
    def data(self, value: gpd.GeoDataFrame):
        self._data = value

    @abstractmethod
    def read(self) -> gpd.GeoDataFrame:
        pass

    def to_file(self, file_path: str, driver: str = 'ESRI Shapefile') -> None:
        if self.data is not None:
            self.data.to_file(file_path, driver=driver)
        else:
            raise ValueError("No data to save. Please read a file first.")


class GeoParquetHandler(GeoDataHandler):
    def read(self) -> gpd.GeoDataFrame:
        """Read GeoParquet file."""
        self.data = gpd.read_parquet(self.file_path)
        return self.data


class ShapefileHandler(GeoDataHandler):
    def read(self) -> gpd.GeoDataFrame:
        """Read ESRI Shapefile."""
        self.data = gpd.read_file(self.file_path)
        return self.data


class GeoJSONHandler(GeoDataHandler):
    def read(self) -> gpd.GeoDataFrame:
        """Read GeoJSON file."""
        self.data = gpd.read_file(self.file_path)
        return self.data


class KMLHandler(GeoDataHandler):
    def read(self) -> gpd.GeoDataFrame:
        """Read KML file."""
        with open(self.file_path, 'r', encoding='utf-8') as kml_file:
            doc = kml_file.read().encode('utf-8')

        kml_data = kml.KML()
        kml_data.from_string(doc)

        features = list(kml_data.features())
        placemarks = list(features[0].features())

        data = []
        for placemark in placemarks:
            data.append({
                'name': placemark.name,
                'geometry': shape(placemark.geometry)
            })

        self.data = gpd.GeoDataFrame(data)
        return self.data


class FileReader:
    _handlers = {
        '.parquet': GeoParquetHandler,
        '.shp': ShapefileHandler,
        '.geojson': GeoJSONHandler,
        '.kml': KMLHandler
    }

    def __init__(self, filepath: Union[str, Path]):
        self.file_path = Path(filepath)

    @staticmethod
    def check_file_validity(filepath) -> Path:
        if isinstance(filepath, (str, Path)):
            filepath = Path(filepath)
            if not filepath.exists():
                raise FileNotFoundError(f"{filepath} does not exist.")
        else:
            raise ValueError("Incorrect filepath type. Expected str or Path.")
        return filepath

    def _get_handler(self) -> GeoDataHandler:
        """Get the appropriate handler based on file extension."""
        extension = self.file_path.suffix.lower()
        handler_class: Type[GeoDataHandler] = FileReader._handlers.get(extension)
        if handler_class is None:
            raise ValueError(f"Unsupported file extension: {extension}")

        return handler_class(self.file_path)

    def read(self) -> gpd.GeoDataFrame:
        """Read the file using the appropriate handler."""
        self.check_file_validity(self.file_path)
        handler = self._get_handler()
        gdf: gpd.GeoDataFrame = handler.read()
        logger.info(f"File {self.file_path} read successfully.")
        return gdf
