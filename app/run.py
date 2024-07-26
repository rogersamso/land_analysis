
import os
from src.cli import parser
from pathlib import Path

from src.suitability_assessment import (SlopeConfig, HANDConfig,
                                        CoverTypeConfig,
                                        Project)

#PROJ_DIR = Path("/app/output")
PROJ_DIR = os.getenv('OUTPUT_DIR', './output')
INPUT_DATA_DIR = os.getenv('INPUT_DIR', './input')


def main(args):

    cover_config = CoverTypeConfig(
        low_suitability_covers=args.low_suit_cover_types,
        medium_suitability_covers=args.medium_suit_cover_types,
        high_suitability_covers=args.high_suit_cover_types)

    slope_config = SlopeConfig(
        low_threshold=args.slope_low_suit_threshold,
        medium_threshold=args.slope_medium_suit_threshold,
        high_threshold=args.slope_high_suit_threshold)

    hand_config = HANDConfig(low_threshold=args.hand_low_suit_threshold,
                             medium_threshold=args.hand_medium_suit_threshold,
                             high_threshold=args.hand_high_suit_threshold)

    land_obj = Project(project_name=args.project_name,
                       project_year=args.project_year,
                       aoi_path=Path(INPUT_DATA_DIR).joinpath(args.aoi_file_name),
                       io=args.io,
                       db_config=None,
                       country_code=args.country_code,
                       sub_region=args.sub_region,
                       years_prior=args.years_prior,
                       epsg=args.epsg,
                       project_dir=Path(PROJ_DIR),
                       intermediate_results_path=None,
                       data_dir=None,
                       administrative_borders_path=Path(INPUT_DATA_DIR).joinpath(args.admin_border),
                       protected_areas_path=Path(INPUT_DATA_DIR).joinpath(args.protected_areas),
                       results_file_path=None
                       )

    stats = land_obj.analyze_land_suitability(
                min_viable_area=args.min_viable_area,
                land_checks=args.land_checks,
                slope_config=slope_config if args.analyze_slope else None,
                cover_config=cover_config if args.analyze_land_cover else None,
                hand_config=hand_config if args.analyze_hand else None,
                reference_raster=args.reference_raster)

    # returns the resulting raster path and the stats json path
    return (land_obj.io_handler.analysis_output_path,
            land_obj.io_handler.stats_path)


if __name__ == "__main__":
    print(os.getcwd())

    args = parser.parse_args()

    raster, stats = main(args)

    print("Ckeck out your local volume folder to see the results.")
