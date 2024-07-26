import sys
from typing import Union, Optional, List, Dict, Callable, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
import geopandas as gpd
import numpy as np
import numpy.typing as npt
import rasterio as rio
from rasterio.crs import CRS
from shapely.geometry import box
import xarray as xr

from .tools import add_word_to_filename
from .io_vector import FileReader
from .data_downloader import DataDownloader
from .io import DiskHandler
from .logging_config import logger

ArrayFunction = Callable[[npt.ArrayLike], npt.ArrayLike]


class Suitability(Enum):
    Low = 1
    Medium = 2
    High = 3

    def __init__(self, code):
        self.code = code


@dataclass
class SlopeConfig:
    low_threshold: float
    high_threshold: float
    medium_threshold: float


@dataclass
class HANDConfig:
    low_threshold: float
    high_threshold: float
    medium_threshold: float


@dataclass
class CoverTypeConfig:
    low_suitability_covers: List[Union[int, str]]
    medium_suitability_covers: List[Union[int, str]]
    high_suitability_covers: List[Union[int, str]]


@dataclass
class Stats:
    project_name: Optional[str] = field(default=None)
    years: Optional[List[int]] = field(default=None)
    project_crs: Optional[int] = field(default=None)
    project_bbox: Optional[Dict[str, float]] = field(default=None)
    aoi_area: Optional[Tuple[float, str]] = field(default=None)
    aoi_within_admin_border_area: Optional[Tuple[float, str]] = field(default=None)
    aoi_outside_admin_border_area: Optional[Tuple[float, str]] = field(default=None)
    intersect_with_protected_area: Optional[Tuple[float, str]] = field(default=None)
    area_non_protected: Optional[Tuple[float, str]] = field(default=None)  # Ha
    # slope
    average_slope: Optional[Tuple[float, str]] = field(default=None)  # %
    max_slope: Optional[Tuple[float, str]] = field(default=None)  # %
    min_slope: Optional[Tuple[float, str]] = field(default=None)  # %
    # land cover
    area_of_adequate_land_cover_over_time: Optional[Tuple[float, str]] = field(default=None)  # %
    # hand
    average_height_above_drainage: Optional[Tuple[float, str]] = field(default=None)
    max_height_above_drainage: Optional[Tuple[float, str]] = field(default=None)
    min_height_above_drainage: Optional[Tuple[float, str]] = field(default=None)
    # suitabilities
    area_low_suitability: Optional[Tuple[float, str]] = field(default=None)
    area_medium_suitability: Optional[Tuple[float, str]] = field(default=None)
    area_high_suitability: Optional[Tuple[float, str]] = field(default=None)


class Project(object):

    def __init__(self,
                 *,
                 project_name: str,
                 project_year: int,
                 aoi_path: Union[str, Path],
                 io: str = "disk",
                 db_config=None,
                 country_code: Optional[str] = "ARG",
                 sub_region: Optional[str] = "Corrientes",
                 years_prior: Optional[int] = 5,
                 epsg: Optional[int] = 32721,
                 project_dir: Optional[Union[str, Path]] = None,
                 intermediate_results_path: Optional[Union[str, Path]] = None,
                 data_dir: Optional[Union[str, Path]] = None,
                 administrative_borders_path: Optional[Union[str, Path]] = None,
                 protected_areas_path: Optional[Union[str, Path]] = None,
                 results_file_path: Optional[Union[str, Path]] = None
                 ):

        """
        The project class is the entry point to all data processing needed to classify the area of interes in Low/Medium/High suitability.
        Relevant methods to this class are analyze_land_suitability, or any of the methods available to perform each individual check.

        This function returns the result as either a raster file, or stores the data directly on a database (this last bit is not implemented).

        Args:
            project_name (str): Name of the project. Used to create a specific storage location for this project results.
            project_year (int): Year at which the project will be developed.
            aoi_path (Union[str, Path]): Path to the file containing the area of interest.
            io (str, optional): Options are disk or db. Through this parameter, the user can select whether to write the results on a database or locally.
            db_config (optional): Configuration details for the connection to a database. Defaults to "disk".
            country_code (str, optional): Code used to get the borders of the country where the project is to be developed. Defaults to "ARG".
            sub_region (str, optional): Code of the sub region (or province) where the project is to be developed. Defaults to "Corrientes".
            years_prior (int): Number of years before project development that need to be analyzed. Defaults to 5.
            epsg (int): CRS to use along the calculations. Defaults to 32721.
            project_dir (Union[str, Path], optional): Directory where to put the results. If not provided, it defaults to a directory named after project_name. Defaults to None.
            intermediate_results_path (Union[str, Path], optional): path where to store intermediate results. Defaults to None.
            data_dir (Union[str, Path], optional): Path where all original datasets will be downloaded and read from. Defeults to None.
            administrative_borders_path (Union[str, Path]): Path to the file containing the boreders of the region. If it does not exist, it will be downloaded. Defaults to None.
            protected_areas_path: (Union[str, Path]): Path to the file containing the protected areas of the region. If it does not exist, it will be downloaded. Defaults to None.
            results_file_path: (Union[str, Path], optional): Path where the resutls should be stored. Defaults to None. If not passed, defautls to project_name/results.


        """
        if io == "disk":
            self.io_handler = DiskHandler()
        elif io == "db":
            logger.warning("Defaulting to disk handler, cause db handler not yet implemened.")
            self.io_handler = DiskHandler()
            # if db_config is None:
            #    raise ValueError("db_config must be provided for database operations")
            # self.io_handler = DbHandler(db_config)
        else:
            raise ValueError("Invalid io argument. Use 'disk' or 'db'.")

        self.project_name = project_name.lower().replace(" ", "_")

        self.country_code = country_code
        self.sub_region = sub_region

        # set the project CRS
        self.crs = CRS.from_epsg(epsg)

        # read the aoi file
        reader = FileReader(aoi_path)
        aoi: gpd.GeoDataFrame = reader.read()
        self.aoi = aoi.to_crs(self.crs)

        # get site bounding box in WGS84, which is the generally default for pystac
        self.aoi_bbox_WGS84 = aoi.to_crs("EPSG:4326").total_bounds

        self.available_land = None

        if not isinstance(project_year, int):
            raise TypeError("Project year must be an integer.")
        if not isinstance(years_prior, int):
            raise TypeError("Years before project must be integer.")

        self.years = range(project_year-years_prior, project_year + 1)

        self.io_handler.define_addresses(
            aoi_path, project_dir, data_dir, intermediate_results_path,
            results_file_path, protected_areas_path,
            administrative_borders_path, self.years)

        # instantiate empty stats object
        self.stats = Stats()

        # update stats
        self.stats.project_name = project_name
        self.stats.years = list(self.years)
        self.stats.project_crs = self.crs.to_epsg()
        self.stats.project_bbox = self.aoi.bounds.iloc[0, :].to_dict()

        # here we will store the paths of the rasters that need to go into the
        # analysis
        self.rasters_to_analyze = []

    @staticmethod
    def handler_decorator(method_name):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                # Call the corresponding method from the handler
                method = getattr(self.io_handler, method_name)
                method(*args, **kwargs)
                # Call the original Project method
                func_result = func(self, *args, **kwargs)
                return func_result
            return wrapper
        return decorator

    @handler_decorator('ensure_addresses_exist')
    def analyze_land_suitability(
         self,
         *,
         min_viable_area: Optional[float] = 100.,
         land_checks: bool = True,
         slope_config: Optional[SlopeConfig] = None,
         cover_config: Optional[CoverTypeConfig] = None,
         hand_config: Optional[HANDConfig] = None,
         reference_raster: Optional[Union[str, Path]] = None,
         rounding_mechanism: Optional[ArrayFunction] = np.floor
         ) -> Stats:

        """
        This is the main method of the Project class.
        It runs as many individual analysis (slope, hand, land cover,
        protected areas, aoi border within region, minimum viable area) as
        configuration arguments are passed to the function, and then uses those
        to produce a raster (geotif) that classifies the land according to
        their suitability (Low (1), Medium (2) and High (3)) for the project at
        hand.

        If any of the analysis have been previously performed on their own,
        and no config files are passed to this function, it will try to find
        intermediate results in the rasters_to_analyze attribute, and use those
        for the analysis.

        NOTE: all arguments to the function must be passed as keyword args
        (e.g. min_viable_area=100, instead of just 100).

        Args:
            min_viable_area (float, optional): Minimum available area for the project, in Ha. Defaults to 100.
            land_checks (bool, optional): Whether to perform protected areas or border checks. Defaults to True.
            slope_config (SlopeConfig, optional): Slope configuration. If passed, the slope checks will be run. Defaults to None.
            cover_config (CoverTypeConfig, optional): Land cover configuration. If passed, the land cover checks will be run. Defaults to None.
            hand_config (HANDConfig, optional): Height above drainage configuration. If passed, the HAND checks will be run. Defaults to None.
            reference_raster (Union[str,Path], optional): Path to a raster file to use as reference to reproject other rasters. Defauls to None.
            rounding_mechanism (ArrayFunction, optional): Method to use to round the land classification result. Defaults to np.floor.
        Raises:
            ValueError: raises if no config files are passed and there are
            no intermediate results in the rasters_to_analyze attribute.
        """

        self.min_viable_area = min_viable_area  # in Ha

        if (not slope_config) and (not cover_config) and (not hand_config):
            if self.rasters_to_analyze:
                str_ = '\n\t'.join(self.rasters_to_analyze)
                logger.info("Since no configurations were passed, "
                            "skip data collection and processing. The "
                            " followiing rasters will be analyzed: \n\t "
                            f"{str_}"
                            )
                if not self.available_land:
                    if land_checks:
                        self.check_aoi_location()
                    else:
                        self.available_land = self.aoi

            else:
                raise ValueError("Please pass configurations to be able to "
                                 "run the analysis.")
        else:
            chain_functions = []
            get_data_inputs = {"dem": False, "land_cover": False, "hand": False}
            rasters_to_process = []

            if slope_config:
                get_data_inputs.update({"dem": True})
                chain_functions.append((self.slope_analysis, slope_config))
                rasters_to_process.append(self.io_handler.dem_file_path)
            if cover_config:
                get_data_inputs.update({"land_cover": True})
                chain_functions.append((self.land_cover_analysis,
                                        cover_config)
                                       )
                rasters_to_process.extend(
                    list(self.io_handler.land_cover_paths.values()))
            if hand_config:
                get_data_inputs.update({"hand": True})
                chain_functions.append((self.hand_analysis, hand_config))
                rasters_to_process.append(self.io_handler.hand_file_path)

            self.get_data(**get_data_inputs)
            if land_checks:
                self.check_aoi_location()
            else:
                self.available_land = self.aoi
            self.process_rasters(reference_raster, rasters_to_process)

            # run the analysis selected by the user
            for func, args in chain_functions:
                func(args)

        self.land_suitability_analyzer(rounding_mechanism)

        self.io_handler.write_stats(self.stats)

        return self.stats

    def land_suitability_analyzer(
            self, rounding_mechanism: Optional[ArrayFunction] = np.floor):

        """
        Takes the processed rasters from the rasters_to_analyze attribute,
        performs map algebra between them, reclassifies the result using the
        rounding_mechanism function, clips the output using the aoi, and
        saves the result as a raster file (tif).

        Args:
            rounding_mechanism (Optional[ArrayFunction], optional): numpy
            function used to round the result of the map algebra. Options
            include np.round, np.ceil or np.floor. Defaults to np.floor.
        """
        if self.available_land is None:
            logger.info("Using the entire aoi for the analysis.")
            self.available_land = self.aoi

        if self.rasters_to_analyze:
            str_ = '\t\n'.join(map(str, self.rasters_to_analyze))
            logger.info("Performing map algebra on "
                        f"{str_}.")
        else:
            logger.error("No rasters to analyze.")
            sys.exit()

        sum_raster = None
        for raster_path in self.rasters_to_analyze:
            xds = self.io_handler.read_raster(raster_path)
            if sum_raster is None:
                sum_raster = xds
            else:
                sum_raster += xds

        avg_raster = sum_raster / len(self.rasters_to_analyze)

        negative_mask = avg_raster < 0
        # redefine de nodata value
        avg_raster = avg_raster.where(~negative_mask, other=-9999)

        result_raster = xr.apply_ufunc(rounding_mechanism,
                                       avg_raster)

        self.io_handler.write_vector(
            self.io_handler.remaining_land_projected_path,
            self.available_land)

        # clip the resulting raster using the aoi
        clipped_raster = result_raster.rio.clip(
            [self.available_land.geometry.union_all()],
            crs=self.available_land.crs,
            drop=True)

        metadata = {
                'driver': 'GTiff',
                'dtype': 'int32',
                'count': 1,
                'width': xds.sizes['x'],
                'height': xds.sizes['y'],
                'crs': xds.rio.crs,
                'transform': xds.rio.transform
        }

        # save the final result raster
        logger.info("Final result stored in: "
                    f"{self.io_handler.analysis_output_path}")
        self.io_handler.write_raster(self.io_handler.analysis_output_path,
                                     clipped_raster, nodata=-9999,
                                     metadata=metadata)

        area_low = Project.calculate_area_of_category(clipped_raster,
                                                      Suitability.Low.code) / 1e4
        area_medium = Project.calculate_area_of_category(clipped_raster,
                                                         Suitability.Medium.code) / 1e4
        area_high = Project.calculate_area_of_category(clipped_raster,
                                                       Suitability.High.code) / 1e4

        self.stats.area_low_suitability = (area_low, "Ha")
        self.stats.area_medium_suitability = (area_medium, "Ha")
        self.stats.area_high_suitability = (area_high, "Ha")

    @handler_decorator('ensure_addresses_exist')
    def get_data(self, dem=True, land_cover=True, hand=True, years=None):

        data_downloader = DataDownloader(self.io_handler.data_dir)

        available_msg = "File {file} already available. Skipping download."

        # check if administrative borders available or download
        if not self.io_handler.address_exists(self.io_handler.region_border_path):
            data_downloader.get_border(self.country_code,
                                       self.io_handler.region_border_path)
        else:
            logger.info(
                available_msg.format(file=self.io_handler.region_border_path))

        # check if protected areas available or download
        if not self.io_handler.address_exists(
             self.io_handler.protected_areas_path):
            data_downloader.get_protected_areas(
                self.country_code, self.io_handler.protected_areas_path)
        else:
            logger.info(
                available_msg.format(file=self.io_handler.protected_areas_path)
                )

        if dem:
            # check if DEM is available, and if it covers the aoi, else download
            if not self.io_handler.address_exists(self.io_handler.dem_file_path
                                                  ) or \
               not Project.is_polygon_within_raster_extent(
                   self.aoi,
                   self.io_handler.read_raster(self.io_handler.dem_file_path)):
                data_downloader.get_dem_planetary_computer(
                    self.aoi_bbox_WGS84, self.io_handler.dem_file_path)
            else:
                logger.info(
                    available_msg.format(file=self.io_handler.dem_file_path))

        if land_cover:
            # Determine which years have missing land cover data
            missing_years = {
                year: path
                for year, path in self.io_handler.land_cover_paths.items()
                if not self.io_handler.address_exists(path)
            }

            for year, path in self.io_handler.land_cover_paths.items():
                if year in missing_years:
                    # for missing data, download it
                    data_downloader.get_land_cover_data(self.aoi_bbox_WGS84,
                                                        year, path)
                else:
                    # for existing data, check its validity
                    xds = self.io_handler.read_raster(path)
                    if Project.is_polygon_within_raster_extent(self.aoi, xds):
                        logger.info(available_msg.format(file=path))
                    else:
                        # if the existing data is not valid, download it
                        data_downloader.get_land_cover_data(
                            self.aoi_bbox_WGS84, year, path)

            # update the available data files and paths and continue with them
            self.io_handler.land_cover_paths = {
                year: path
                for year, path in self.io_handler.land_cover_paths.items()
                if self.io_handler.address_exists(path)}

        if hand:
            if not self.io_handler.address_exists(self.io_handler.hand_file_path) or \
                not Project.is_polygon_within_raster_extent(
                   self.aoi,
                   self.io_handler.read_raster(self.io_handler.hand_file_path)
                   ):

                data_downloader.get_hand_data(self.aoi_bbox_WGS84,
                                              self.io_handler.hand_file_path)
            else:
                logger.info(available_msg.format(
                    file=self.io_handler.hand_file_path))

        logger.info("Finished downloading all required datasets.")

    @handler_decorator('ensure_addresses_exist')
    def process_rasters(
            self,
            reference_raster: Optional[Union[str, Path]] = None,
            rasters_to_process: Optional[List[Path]] = None):

        """
        Takes a raster as a reference, clips it with the aoi shape,
        projects it using the CRS passed by the user.

        Args:
            reference_raster (Optional[Union[str, Path]], optional): Reference
            raster path. Defaults to None.
        """

        # I use the dem as reference because it is at 30m resolution
        reference_raster = (Path(reference_raster) if reference_raster
                            else self.io_handler.dem_file_path)

        logger.info(f"Performing raster processing, using {reference_raster} "
                    "as reference.")

        if not rasters_to_process:
            # we process them all
            rasters_to_process = [self.io_handler.dem_file_path] + \
                                 list(self.io_handler.land_cover_paths.values()) + \
                                 [self.io_handler.hand_file_path]

        # get only those that exist
        available_rasters = []
        for path in rasters_to_process:
            if path.is_file():
                available_rasters.append(path)
            else:
                logger.warning(f"{path} is not available and will not "
                               "be processed")

        # load reference xds
        ref_xds = self.io_handler.read_raster(reference_raster)

        # clip the reference raster around the available land, but with the
        # ref_xds EPSG
        temp_available_land_crs1 = self.available_land.to_crs(ref_xds.rio.crs)
        bbox1 = temp_available_land_crs1.bounds.iloc[0, :].to_dict()
        ref_xdsc = ref_xds.rio.clip_box(**bbox1)

        # reproject ref dataset to the project EPSG
        ref_xdsc_proj = ref_xdsc.rio.reproject(self.crs)
        # reproject remaining aoi

        logger.info(f"All rasters will be reprojected to {self.crs.data['init']}")

        for file in available_rasters:
            result_path = add_word_to_filename(
                self.io_handler.intermediate_results_dir.joinpath(file.name))

            if result_path.is_file():
                logger.warning(f"Overriding {result_path}.")

            if file == reference_raster:
                self.io_handler.write_raster(result_path, ref_xdsc_proj)
            else:
                xds = self.io_handler.read_raster(file)
                # get available land to CRS of xds
                temp_available_land_crs2 = self.available_land.to_crs(
                    xds.rio.crs)
                # cut xds with available land at xds CRS
                bbox2 = temp_available_land_crs2.bounds.iloc[0, :].to_dict()
                xdsc = xds.rio.clip_box(**bbox2)
                xdsc_proj = xdsc.rio.reproject_match(ref_xdsc_proj)
                self.io_handler.write_raster(result_path, xdsc_proj)

    @handler_decorator('ensure_addresses_exist')
    def slope_analysis(self, slope_config: Optional[SlopeConfig] = None):

        logger.info("Performing slope analysis.")

        xds = self.io_handler.read_raster(
            self.io_handler.dem_file_path_projected)

        # Read the elevation data
        elevation_data = xds.values

        # Assume cellsize from the transform
        transform = xds.rio.transform()
        cellsize = transform[0]

        slope_data: np.array = Project.calculate_slope(
                elevation_data, cellsize)

        # copy the metadata
        meta_slopes = xds.attrs.copy()
        meta_slopes.update(dtype=rio.float32)

        meta_slopes_classified = xds.attrs.copy()
        meta_slopes_classified['dtype'] = 'uint32'

        classified_slopes: np.array = self._reclassify(slope_data,
                                                       slope_config)

        # Save intermediate result to file
        slope_data_xr = xr.DataArray(slope_data,
                                     coords=xds.coords,
                                     dims=xds.dims,
                                     attrs=meta_slopes)

        # Write the slope data to a new GeoTIFF
        slope_data_xr.rio.write_crs(xds.rio.crs, inplace=True)
        self.io_handler.write_raster(self.io_handler.slope_path, slope_data_xr)

        # Save intermediate result to file
        slope_data_classified_xr = xr.DataArray(classified_slopes,
                                                coords=xds.coords,
                                                dims=xds.dims,
                                                attrs=meta_slopes_classified)

        # Write classified slope data to a new GeoTIFF
        slope_data_classified_xr.rio.write_crs(xds.rio.crs, inplace=True)
        self.io_handler.write_raster(self.io_handler.reclassified_slope_path,
                                     slope_data_classified_xr)

        logger.info(f"Slope raster saved to {self.io_handler.slope_path}.")
        logger.info("Slope raster reclassified saved to "
                    f"{self.io_handler.reclassified_slope_path}.")

        self.rasters_to_analyze.append(self.io_handler.reclassified_slope_path)

        # update stats
        slope_data_xr_clipped = slope_data_xr.rio.clip(
            [self.available_land.geometry.union_all()],
            crs=self.available_land.crs)

        self.stats.average_slope = (float(np.nanmean(slope_data_xr_clipped)),
                                    "%")
        self.stats.max_slope = (float(np.nanmax(slope_data_xr_clipped)), "%")
        self.stats.min_slope = (float(np.nanmin(slope_data_xr_clipped)), "%")

    @handler_decorator('ensure_addresses_exist')
    def land_cover_analysis(self, cover_config: CoverTypeConfig):

        logger.info("Performing land cover analysis.")

        self.min_usable_land_cover_over_years(cover_config)

        self.rasters_to_analyze.append(
            self.io_handler.result_land_cover_path_reclassified)

    @handler_decorator('ensure_addresses_exist')
    def hand_analysis(self,
                      hand_config: Optional[HANDConfig] = None
                      ) -> Optional[Stats]:

        logger.info("Performing HAND analysis.")

        xds = self.io_handler.read_raster(
            self.io_handler.hand_file_path_projected)

        hand_data = xds.data

        xds_clipped = xds.rio.clip([self.available_land.geometry.union_all()],
                                   crs=self.available_land.crs,
                                   drop=True)
        self.stats.average_height_above_drainage = (
            float(np.nanmean(xds_clipped)), "m")
        self.stats.min_height_above_drainage = (float(np.nanmin(xds_clipped)),
                                                "m")
        self.stats.max_height_above_drainage = (float(np.nanmax(xds_clipped)),
                                                "m")

        meta = xds.attrs.copy()

        # ensure the data type uint
        meta['dtype'] = 'uint32'

        classified_hand: np.array = self._reclassify(hand_data,
                                                     hand_config)

        classified_hand_xr = xr.DataArray(classified_hand,
                                          dims=xds.dims,
                                          coords=xds.coords,
                                          attrs=meta)

        # Write the hand data to a new GeoTIFF
        classified_hand_xr.rio.write_crs(xds.rio.crs, inplace=True)

        self.io_handler.write_raster(
            self.io_handler.reclassified_hand_result_path,
            classified_hand_xr)

        self.rasters_to_analyze.append(
            self.io_handler.reclassified_hand_result_path)

    @handler_decorator('ensure_addresses_exist')
    def min_usable_land_cover_over_years(
        self,
        config: CoverTypeConfig,
        file_paths: Optional[Dict[int, Union[Path, str]]] = None,
        classified_land_cover_path: Optional[Union[str, Path]] = None,
        no_data_class: Optional[int] = 0,
        clouds_class: Optional[int] = 10
         ) -> gpd.GeoDataFrame:

        """
        Opens land cover rasters for the specified years, masks clouds and
        nodata, values, creates a mask that contains the minimum area covered
        by the specified land cover types along all years, and reclassifies
        the areas based on the criteria defined in config.
        Writes the slope in degrees in one file, and the reclassified slopes in
        another file.

        """

        file_paths = (self.io_handler.land_cover_paths_projected
                      if not file_paths
                      else {year: Path(path)
                            for year, path in file_paths.items()
                            }
                      )

        # Get only those that are available
        file_paths = {year: path
                      for year, path in file_paths.items()
                      if path.is_file()}

        # uses either the path passed by the user or the default
        classified_land_cover_path = (
            Path(classified_land_cover_path)
            if classified_land_cover_path else
            self.io_handler.result_land_cover_path_reclassified)

        # Collect only the viable land cover types
        viable_categories = (
            config.low_suitability_covers +
            config.medium_suitability_covers +
            config.high_suitability_covers
        )

        combined_mask = None

        last_year = max(file_paths.keys())

        for year, fname in file_paths.items():

            xds = self.io_handler.read_raster(fname)

            # Mask No Data and Clouds
            xds = xds.where(
                (xds != no_data_class) &
                (xds != clouds_class),
                np.nan)

            if year == last_year:
                last_data_array = xds

            data = xds.values

            # Create a mask for viable categories
            mask = np.isin(data, viable_categories)

            if combined_mask is None:
                combined_mask = mask
            else:
                combined_mask = np.logical_and(combined_mask, mask)

        # extract metadata and ensure the data type is float32
        meta = last_data_array.attrs
        meta['dtype'] = 'int32'

        # set values of last year to the combined mask, else np.nan
        result: np.array = np.where(combined_mask, last_data_array.data, np.nan)

        # Save intermediate result to file
        result_raster = xr.DataArray(result,
                                     coords=last_data_array.coords,
                                     dims=last_data_array.dims,
                                     attrs=meta)

        # update stats
        raster_cut = result_raster.rio.clip(
            [self.available_land.geometry.union_all()],
            crs=self.available_land.crs,
            drop=True)

        viable_area = Project.calculate_area_of_category(raster_cut,
                                                         viable_categories)
        self.stats.area_of_adequate_land_cover_over_time = (viable_area / 1e4,
                                                            "Ha")

        result_raster.rio.write_crs(last_data_array.rio.crs, inplace=True)
        self.io_handler.write_raster(self.io_handler.result_land_cover_path,
                                     result_raster)

        # reclassify land cover
        classified_land_cover: np.array = \
            self._reclassify_land_cover(result, config)

        classified_data_array = xr.DataArray(classified_land_cover,
                                             coords=last_data_array.coords,
                                             dims=last_data_array.dims,
                                             attrs=meta
                                             )

        # Save the classified land cover
        classified_data_array.rio.write_crs(last_data_array.rio.crs,
                                            inplace=True)
        self.io_handler.write_raster(classified_land_cover_path,
                                     classified_data_array, nodata=-9999)

    @staticmethod
    def calculate_slope(elevation: np.ndarray, cellsize: float) -> np.ndarray:
        """
        Calculate slope from elevation data.
        :param elevation: 2D numpy array of elevation values
        :param cellsize: Size of a cell (assumed square)
        :return: 2D numpy array of slope values
        """
        # Calculate gradient
        dzdx = np.gradient(elevation, axis=1) / cellsize
        dzdy = np.gradient(elevation, axis=0) / cellsize

        # Calculate slope in degrees
        slope = np.sqrt(dzdx**2 + dzdy**2)
        slope = np.arctan(slope) * (180 / np.pi)

        return slope

    @handler_decorator('ensure_addresses_exist')
    def check_aoi_location(self) -> gpd.GeoDataFrame:

        """
        Calculates the following areas:
        - Area of intersection between aoi and administrative borders
        - Area of intersection between aoi and protected areas

        Returns:
            gpd.GeoDataFrame: Available land after intersctions with admin
            borders and protected areas

        """

        # all the estimations made here will the epsg passed by the user

        aoi_border_overlay = self._aoi_within_admin_borders(self.aoi.crs)

        # estimate intersection between area in region and protected areas
        protected_areas = self._load_protected_areas_polygons(self.aoi.crs)

        # Calculate the intersection with protected areas in WGS84
        aoi_border_prot_inters = gpd.overlay(aoi_border_overlay,
                                             protected_areas,
                                             how='intersection')

        # calculate areas in Ha
        aoi_original_area = self.aoi.geometry[0].area / 1e4

        aoi_border_overlay["area"] = aoi_border_overlay.geometry.area / 1e4
        aoi_within_borders_area = aoi_border_overlay["area"].sum()

        if aoi_within_borders_area < aoi_original_area:
            logger.warning(
                f"Area of interest partially outside {self.sub_region}.")

        if aoi_within_borders_area < self.min_viable_area:
            logger.error(
                f"Area of interest ({aoi_within_borders_area} Ha) below viable "
                "area ({self.min_viable_area})")
            sys.exit()

        if not aoi_border_prot_inters.empty: # if part of the aoi is protected

            aoi_border_prot_inters['area'] = aoi_border_prot_inters['geometry'].area / 1e4
            area_aoi_border_prot_inters = aoi_border_prot_inters['area'].sum()

            if aoi_within_borders_area == area_aoi_border_prot_inters:
                logger.error(
                    f"Area of interest falls completely within a protected "
                    "area.")
                sys.exit()
            else:
                non_protected_area = (aoi_within_borders_area -
                                      area_aoi_border_prot_inters)

                if non_protected_area < self.min_viable_area:
                    logger.error(
                        f"Area of interest outside of protected areas ("
                        f"{non_protected_area}) is below viable "
                        f"area ({self.min_viable_area})")
                    sys.exit()

            logger.warning(
                "At least a chunk of the area of interest is protected.")

            # calculate the difference with protected areas, which will
            # be the remaining land
            remaining_land = gpd.overlay(aoi_border_overlay,
                                         protected_areas,
                                         how='difference')

        else:
            logger.info("No intersection found with protected areas.")
            area_aoi_border_prot_inters = 0
            non_protected_area: float = aoi_within_borders_area
            remaining_land: gpd.GeoDataFrame = aoi_border_overlay

        # update stats
        self.stats.aoi_area = (aoi_original_area, "Ha")
        self.stats.aoi_within_admin_border_area = (aoi_within_borders_area,
                                                   "Ha")
        self.stats.aoi_outside_admin_border_area = (
            aoi_original_area - aoi_within_borders_area, "Ha")
        self.stats.intersect_with_protected_area = (
            area_aoi_border_prot_inters, "Ha")
        self.stats.area_non_protected = (non_protected_area, "Ha")

        self.available_land = remaining_land

    def _reclassify(self, original_array: np.array,
                    config: Union[SlopeConfig, HANDConfig]):

        # create an empty array for the results
        reclassified_array = np.empty_like(original_array, dtype="uint32")

        # define conditions based on the configuration
        condition_low = (original_array < config.low_threshold) | (original_array > config.medium_threshold)
        condition_high = (original_array >= config.low_threshold) & (original_array < config.high_threshold)
        condition_medium = ~condition_low & ~condition_high

        # assign the suitability based on conditions
        reclassified_array[condition_low] = Suitability.Low.code
        reclassified_array[condition_high] = Suitability.High.code
        reclassified_array[condition_medium] = Suitability.Medium.code

        return reclassified_array

    def _reclassify_land_cover(self, original_array: np.array,
                               config: CoverTypeConfig):

        # Create an empty array for the results
        reclassified_array = np.empty_like(original_array, dtype="int32")
        condition_nans = np.isnan(original_array)
        condition_low = np.isin(original_array,
                                config.low_suitability_covers)
        condition_medium = np.isin(original_array,
                                   config.medium_suitability_covers)
        condition_high = np.isin(original_array,
                                 config.high_suitability_covers)

        reclassified_array[condition_nans] = -9999
        reclassified_array[condition_low] = Suitability.Low.code
        reclassified_array[condition_high] = Suitability.High.code
        reclassified_array[condition_medium] = Suitability.Medium.code

        return reclassified_array

    def _aoi_within_admin_borders(self, crs) -> gpd.GeoDataFrame:

        admin_border: gpd.GeoDataFrame = self._load_region_subregion_polygon(crs)

        if admin_border.crs != crs:
            admin_border = admin_border.to_crs(crs)

        aoi_border_overlay = gpd.overlay(admin_border, self.aoi, how='intersection')

        if aoi_border_overlay.shape[0] == 0:
            logger.error("Area of interest not within administrative borders "
                         f"of {self.country_code}-{self.sub_region}.")
            sys.exist()

        return aoi_border_overlay

    def _load_region_subregion_polygon(self, crs) -> gpd.GeoDataFrame:

        if not self.io_handler.address_exists(
             self.io_handler.region_border_path):
            raise FileNotFoundError("Administrative borders for the project "
                                    "not found. Please run the get_data method"
                                    " before continuing.")

        region_border_gdf: gpd.GeoDataFrame = self.io_handler.read_vector(
            self.io_handler.region_border_path)

        if region_border_gdf.crs != crs:
            region_border_gdf = region_border_gdf.to_crs(crs)

        # Filter the GeoDataFrame for sub_region
        sub_region_gdf = region_border_gdf[
                region_border_gdf['NAME_1'] == self.sub_region
                ]

        if sub_region_gdf.shape[0] == 0:
            raise KeyError(f" Invalid subregion ({self.sub_region})"
                           f"for country: {self.country}")

        return sub_region_gdf

    def _load_protected_areas_polygons(self, crs) -> gpd.GeoDataFrame:

        if not self.io_handler.protected_areas_path.exists():
            raise FileNotFoundError(
                "The data on protected areas could not be loaded from "
                f"{self.io_handler.protected_areas_path}")

        protected_gdf = self.io_handler.read_vector(self.io_handler.protected_areas_path)

        if protected_gdf.crs != crs:
            protected_gdf = protected_gdf.to_crs(crs)

        return protected_gdf

    @staticmethod
    def is_polygon_within_raster_extent(polygon: gpd.GeoDataFrame,
                                        raster: xr.DataArray) -> bool:

        """
        Check if the bounding box of a polygon is within the raster's bounding
        box.

        Parameters:
        - raster (rioxarray.DataArray): The raster data array.
        - polygon (gpd.GeoDataFrame): A GeoDataFrame containing the
        polygon(s)
        to check.

        Returns:
        - bool: True if the polygon's bounding box is within the raster's
        bounding
        box, False otherwise.
        """

        # Get the bounding box of the raster
        raster_bounds = raster.rio.bounds()
        raster_bbox = box(raster_bounds[0],
                          raster_bounds[1],
                          raster_bounds[2],
                          raster_bounds[3])

        # reproject aoi to raster crs (just in case)
        raster_crs = raster.rio.crs
        polygon_reprojected = polygon.to_crs(raster_crs)

        # Get the bounding box of the polygon
        polygon_bounds = polygon_reprojected.union_all().envelope
        polygon_bbox = box(polygon_bounds.bounds[0],
                           polygon_bounds.bounds[1],
                           polygon_bounds.bounds[2],
                           polygon_bounds.bounds[3])

        # Check if the polygon bounding box is within the raster bounding box
        is_within = raster_bbox.contains(polygon_bbox)

        return is_within

    def calculate_area_of_category(raster: xr.DataArray, categories: int
                                   ) -> np.float32:

        """
        Calculates the area of specific categories in a raster. It does not
        change the units.

        Returns:
            np.float32: area of the selected categories
        """

        mask = np.isin(raster, categories)
        pixel_size_x = abs(raster.rio.resolution()[0])
        pixel_size_y = abs(raster.rio.resolution()[1])

        # Calculate the area of each pixel
        pixel_area = pixel_size_x * pixel_size_y

        masked_pixel_count = np.sum(mask)

        total_masked_area = masked_pixel_count * pixel_area

        return total_masked_area
