import argparse
from pathlib import Path
import os

INPUT_DATA_DIR = os.getenv('INPUT_DIR', './input')

PROJECT_DIR = Path(__file__).parent.parent
ADMIN_BORDER = Path(INPUT_DATA_DIR).joinpath("admin_border_ARG.geojson")
PROTECTED = Path(INPUT_DATA_DIR).joinpath("protected_areas_ARG.geojson")

land_covers = {0: "No Data",
               1: 'Water',
               2: 'Trees',
               4: 'Flooded vegetation',
               5: 'Crops',
               7: 'Built area',
               8: 'Bare ground',
               9: 'Snow/ice',
               10: 'Clouds',
               11: 'Rangeland'}

land_covers_str = "Land cover types in MS Planetary Computer:\n"
for key, value in land_covers.items():
    land_covers_str += f"    {key}: {value}"

default_slope_suitability_config = ("Default_configuration: "
                                    "low suitability slopes: < 1%% and > 5%%, "
                                    " high suitability slopes: 1%% to 3%%, "
                                    " medium suitability slopes: > 3%% to 5%%.")

default_hand_suitability = ("Default configuration: "
                            "low suitability hand: < 1m and > 50m,"
                            " high suitability slopes: 1m to 30m,"
                            " medium suitability slopes: > 30m to 50m.")

default_land_cover_suitabilities = ("Default land cover suitabilities: "
                                    "low suitability land covers: Crops, "
                                    "medium suitability land covers: None, "
                                    "high suitability land covers: Bare "
                                    "ground and Rangeland.")

# define the arguments of the CLI
parser = argparse.ArgumentParser(description="CLI interface arguments to do land suitability analysis")
parser.add_argument("--project_name", type=str, default="corrientes", help="Project name (default: corrientes)")
parser.add_argument("--project_year", type=int, default=2025, help="Project year (default: 2025)")
parser.add_argument("--aoi_file_name", type=str, required=True, help="Name of the file containing the area of interest of the project")
parser.add_argument("--io", type=str, default="disk", help="IO method to use (default: disk, options are disk or db)")
parser.add_argument("--db_config", default=None, help="Database configuration (not implemented, for now)")
parser.add_argument("--country_code", type=str, default="ARG", help="Country code (default: ARG)")
parser.add_argument("--sub_region", type=str, default="Corrientes", help="Sub-region (default: Corrientes)")
parser.add_argument("--years_prior", type=int, default=5, help="Collect data for this many years before the project execution (default: 5 years)")
parser.add_argument("--epsg", type=int, default=32721, help="EPSG code (default: 32721)")
parser.add_argument("--admin_border", type=str, default=ADMIN_BORDER, help=f"Administrative borders path (default is {str(ADMIN_BORDER)})")
parser.add_argument("--protected_areas", type=str, default=PROTECTED, help=f"Path to the file containing protected areas in the regions (default is {str(PROTECTED)})")
parser.add_argument("--min_viable_area", type=float, default=100., help="Minimum viable area for the project (default: 100.0 Ha)")
parser.add_argument("--reference_raster", type=str, default=None, help="Reference raster path. If passed, all other input rasters will use this particular file's data resolution.")

parser.add_argument("--land_checks", type=bool, default=True, help="Perform land checks (default: True)")

parser.add_argument("--analyze_slope", type=bool, default=True,
                    help="Analyze slope (default: True). " + default_slope_suitability_config)
parser.add_argument("--slope_low_suit_threshold", type=float, default=1, help="Low value of slope suitability range (default: 1%%)")
parser.add_argument("--slope_medium_suit_threshold", type=float, default=5, help="Medium value of slope suitability range (default: 5%%)")
parser.add_argument("--slope_high_suit_threshold", type=float, default=3, help="Highest value of slope suitability range (default: 3%%)")

parser.add_argument("--analyze_land_cover", type=bool, default=True,
                    help="Analyze land cover (default: True). " + land_covers_str.strip() + ". " + default_land_cover_suitabilities)
parser.add_argument('--low_suit_cover_types', type=int, nargs='*', default=[5], help='Low suitability land cover types (default: Crops)')
parser.add_argument('--medium_suit_cover_types', type=int, nargs='*', default=[], help='Medium suitability land cover types (default: None)')
parser.add_argument('--high_suit_cover_types', type=int, nargs='*', default=[8, 11], help='High suitability land cover types (default: Bare ground (8) and Rangeland (11))')

parser.add_argument("--analyze_hand", type=bool, default=True, help="Analyze HAND (default: True) " + default_hand_suitability)
parser.add_argument("--hand_low_suit_threshold", type=float, default=1, help="Low value of hand suitability range (default: 1 m)")
parser.add_argument("--hand_medium_suit_threshold", type=float, default=50., help="Medium value of hand suitability range (default: 50 m)")
parser.add_argument("--hand_high_suit_threshold", type=float, default=30., help="Highest value of hand suitability range (default: 30 m)")
