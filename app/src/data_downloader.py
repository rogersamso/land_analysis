from typing import List
import requests
from requests.exceptions import HTTPError, RequestException
from typing import Union
from pathlib import Path

from pystac_client import Client
import planetary_computer
import geopandas as gpd

from .logging_config import logger


class DataDownloader():

    def __init__(self, data_dir: Union[str, Path]):

        self.data_dir = Path(data_dir)

        # create data dir if it does not exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_border(country_code: str, region_border_path) -> gpd.GeoDataFrame:

        url = f"https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{country_code}_1.json"

        # Load the data into a GeoDataFrame
        try:
            response = requests.get(url)
            response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
            with open(region_border_path, 'wb') as f:
                f.write(response.content)
        except HTTPError as e:
            raise HTTPError(f"HTTPError: {e}")
        except RequestException as e:
            # Handle other requests exceptions (like connection errors, timeouts, etc.)
            raise RequestException(f"RequestException: {e}")
        except Exception as e:
            # Handle other potential errors
            raise Exception(f"An error occurred: {e}")

    @staticmethod
    def search_items_from_stac_catalog(client,
                                       collections,
                                       bbox: gpd.GeoDataFrame,
                                       modifier=None,
                                       date=None):

        catalog = Client.open(
            client,
            modifier=modifier,
        )

        search = catalog.search(
            collections=collections,
            #intersects=project_area,
            bbox=bbox,
            datetime=str(date) if date else None
        )

        items = list(search.items())

        if not items:
            logger.error(f"No items found in the search results from {client}.")
        else:
            logger.info(f"{client} catalog search returned {len(items)} items")

        return items

    @staticmethod
    def download_items_from_stac_catalog(item_url, result_path):

        logger.info(f"Found data at URL: {item_url}")

        response = requests.get(item_url, stream=True)

        if response.status_code == 200:
            # Write the file to the local filesystem
            with open(result_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"File downloaded and saved as {result_path}")
        else:
            logger.error(f"Failed to download file. Status code: {response.status_code}")

    @staticmethod
    def get_dem_planetary_computer(bbox, result_path: Union[str, Path]):

        client = "https://planetarycomputer.microsoft.com/api/stac/v1"
        collections = ["cop-dem-glo-30"]
        modifier = planetary_computer.sign_inplace

        logger.info("Downloading dem from Microsoft's Planetary "
                    "Computer catalog (collection: {collections[0]})")

        items: List = DataDownloader.search_items_from_stac_catalog(
            client, collections, bbox, modifier=modifier)

        if items:
            signed_asset = planetary_computer.sign(items[0].assets["data"])
            item_url = signed_asset.href

            DataDownloader.download_items_from_stac_catalog(item_url, result_path)

    @staticmethod
    def get_hand_data(bbox, hand_path: Union[str, Path]):
        logger.info("Downloading HAND data from Planetary GLO-30 HAND Catalog")

        client = 'https://stac.asf.alaska.edu/'
        collections = ['glo-30-hand']

        items: List = DataDownloader.search_items_from_stac_catalog(
            client, collections, bbox)

        if items:
            item_url = items[0].assets['data'].href

            DataDownloader.download_items_from_stac_catalog(item_url, hand_path)

    @staticmethod
    def get_land_cover_data(bbox, date, land_cover_path: Union[str, Path]):
        logger.info("Downloading land cover data from Planetary Computer Catalog")

        client = "https://planetarycomputer.microsoft.com/api/stac/v1"
        collections = ["io-lulc-annual-v02"]

        items = DataDownloader.search_items_from_stac_catalog(
                client, collections, bbox, date=date)

        if items:
            item_url = items[0].assets['data'].href

            DataDownloader.download_items_from_stac_catalog(item_url, land_cover_path)

    @staticmethod
    def get_protected_areas(country_code: str, result_path: Union[str, Path]):
        raise NotImplementedError("I cannot download protected areas yet!")
