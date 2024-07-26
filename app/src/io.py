
import json
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import asdict

from typing import Union

# import psycopg2
# from psycopg2.extras import RealDictCursor
import rioxarray as rxr
import geopandas as gpd
import numpy as np

from .io_vector import FileReader
from .tools import add_word_to_filename


# Abstract Base Class for Data Handlers
class DataHandler(ABC):
    @abstractmethod
    def read_raster(self, path):
        pass

    @abstractmethod
    def write_raster(self, path, data):
        pass

    @abstractmethod
    def read_vector(self, path):
        pass

    @abstractmethod
    def write_vector(self, path, data):
        pass

    @abstractmethod
    def write_stats(self):
        pass

    @abstractmethod
    def address_exists(self, address):
        pass

    @abstractmethod
    def ensure_addresses_exist(self, *args, **kwargs):
        raise NotImplementedError


# Concrete class for Disk operations
class DiskHandler(DataHandler):
    def read_raster(self, path):
        return rxr.open_rasterio(path, masked=True).squeeze()

    def write_raster(self, path, data, nodata=np.nan, metadata=None):
        data.rio.to_raster(path, nodata=nodata, metadata=metadata)

    def read_vector(self, path):
        reader = FileReader(path)
        return reader.read()

    def write_vector(self, path: Union[str, Path], data: gpd.GeoDataFrame):
        data.to_file(path, driver='GeoJSON')

    def write_stats(self, stats):
        with open(self.stats_path, 'w') as json_file:
            json.dump(asdict(stats), json_file, indent=4)

    def ensure_addresses_exist(self, *args, **kwargs):

        self._create_dirs()

    def define_addresses(self, aoi_address, project_dir, data_dir,
                         intermediate_data_dir, results_dir,
                         protected_areas_dir, administrative_borders_dir,
                         years):

        # the data directory will be that of the passed file
        self.aoi_path = Path(aoi_address)
        self.aoi_dir = self.aoi_path.parent

        # create project folder and data folder inside
        self.project_dir = (Path(project_dir)
                            if project_dir
                            else self.aoi_dir.joinpath(self.project_name))

        self.data_dir = (Path(data_dir)
                         if data_dir
                         else self.project_dir.joinpath("data"))
        self.results_dir = self.project_dir.joinpath("results")
        self.intermediate_results_dir = (Path(intermediate_data_dir)
                                         if intermediate_data_dir
                                         else self.project_dir.joinpath(
                                             "intermediate_results"))

        self.stats_path = self.results_dir.joinpath("stats.json")
        self.protected_areas_path = (
            Path(protected_areas_dir) if protected_areas_dir
            else self.project_dir.joinpath(
             f"protected_areas_{self.country_code}.geojson"
            )
        )

        self.region_border_path = (
            Path(administrative_borders_dir)
            if administrative_borders_dir
            else self.project_dir.joinpath(
                f"admin_border_{self.country_code}.geojson")
            )

        self.analysis_output_path = (Path(results_dir)
                                     if results_dir
                                     else self.results_dir.joinpath(
                                         'classified_land.tif')
                                     )

        self.dem_file_path = self.data_dir.joinpath("dem.tif")
        self.dem_file_path_projected = self.intermediate_results_dir.joinpath(
            "dem_processed.tif")

        self.land_cover_paths = {
                year: self.data_dir.joinpath(f"lc_{year}.tif")
                for year in years}

        self.land_cover_paths_projected = {
            year: self.intermediate_results_dir.joinpath(
                f"lc_{year}_processed.tif")
            for year, path in self.land_cover_paths.items()}

        self.hand_file_path = self.data_dir.joinpath("hand.tif")
        self.hand_file_path_projected = \
            self.intermediate_results_dir.joinpath("hand_processed.tif")
        self.reclassified_hand_result_path = \
            add_word_to_filename(
                self.hand_file_path_projected, "reclassified")

        self.slope_path = self.intermediate_results_dir.joinpath("slope.tif")
        self.reclassified_slope_path = \
            add_word_to_filename(self.slope_path, "reclassified")

        self.result_land_cover_path = self.intermediate_results_dir.joinpath(
            "land_cover_intersect.tif")
        self.result_land_cover_path_reclassified = \
            add_word_to_filename(
                self.result_land_cover_path, "reclassified")

        self.remaining_land_projected_path = self.results_dir.joinpath(
            "remaining_land.geojson")

    def _create_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_results_dir.mkdir(parents=True, exist_ok=True)

    def address_exists(self, address: Path) -> bool:
        return address.exists()


# Concrete class for Database operations
class DbHandler(DataHandler):
    def __init__(self, db_config):
        self.db_config = db_config
        # self.connection = psycopg2.connect(**db_config)
        # self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)

    def read_raster(self, path):
        # Implement logic to read raster from the database
        # self.cursor.execute("SELECT raster_data FROM rasters WHERE path = %s", (path,))
        # return self.cursor.fetchone()['raster_data']
        pass

    def write_raster(self, path, data):
        # Implement logic to write raster to the database
        """
        self.cursor.execute(
            "INSERT INTO rasters (path, raster_data) VALUES (%s, %s) ON CONFLICT (path) DO UPDATE SET raster_data = %s",
            (path, data, data)
        )
        self.connection.commit()
        """
        pass

    def read_vector(self, path):
        # Implement logic to read vector from the database
        # self.cursor.execute("SELECT vector_data FROM vectors WHERE path = %s", (path,))
        # return self.cursor.fetchone()['vector_data']
        pass

    def write_vector(self, path, data):
        # Implement logic to write vector to the database
        """
        self.cursor.execute(
            "INSERT INTO vectors (path, vector_data) VALUES (%s, %s) ON CONFLICT (path) DO UPDATE SET vector_data = %s",
            (path, data, data)
        )
        self.connection.commit()
        """
        pass

    def write_stats(self):
        pass

    def ensure_addresses_exist(self, *args, **kwargs):
        pass

    def __del__(self):
        #self.connection.close()
        pass
