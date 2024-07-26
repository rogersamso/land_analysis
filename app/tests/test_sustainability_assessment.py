import pytest

from .conftest import TESTS_DIR, TESTS_DATA_DIR
from src.suitability_assessment import (Project,
                                        Stats,
                                        CoverTypeConfig,
                                        HANDConfig,
                                        SlopeConfig)
from src.data_downloader import DataDownloader

protected_path = TESTS_DATA_DIR.joinpath("protected_areas_ARG.geojson")
borders_path = TESTS_DATA_DIR.joinpath("ARG.geojson")

outside_borders_path = TESTS_DATA_DIR.joinpath("outside_borders")
aoi_path_out = outside_borders_path.joinpath("area_intersects_border.geojson")
intermediate_results_path_out = outside_borders_path.joinpath("intermediate_results")
data_path_out = outside_borders_path.joinpath("data")
results_path_out = outside_borders_path.joinpath("resutls")
# aoi_path_in = outside_borders_path.joinpath("area_of_interest_example.geojson")


@pytest.fixture(scope="session")
def cover_config():

    config = CoverTypeConfig(low_suitability_covers=[5],
                             medium_suitability_covers=[],
                             high_suitability_covers=[8, 11])
    return config


@pytest.fixture(scope="session")
def hand_config():
    config = HANDConfig(low_threshold=1,
                        medium_threshold=50,
                        high_threshold=30)
    return config


@pytest.fixture(scope="session")
def slope_config():
    config = SlopeConfig(low_threshold=1,
                         medium_threshold=5,
                         high_threshold=3)
    return config


@pytest.fixture()
def temp_project_path(tmp_path):
    temp_project_path = tmp_path.joinpath("test_project")
    temp_project_path.mkdir(parents=True, exist_ok=True)

    return temp_project_path


@pytest.fixture()
def project(temp_project_path):

    project = Project(project_name="Corrientes",
                      project_year=2025,
                      aoi_path=aoi_path_out,
                      protected_areas_path=protected_path,
                      administrative_borders_path=borders_path,
                      project_dir=temp_project_path
                      )

    return project


def test_project_create_dirs(temp_project_path, project):

    assert project.io_handler.data_dir == temp_project_path.joinpath("data")

    # create directories if they don't exist
    project.io_handler._create_dirs()

    assert project.io_handler.address_exists(project.io_handler.data_dir)
    assert project.io_handler.address_exists(project.io_handler.results_dir)
    assert project.io_handler.address_exists(
        project.io_handler.intermediate_results_dir)


def test_analyze_land_suitability_no_configs_raises(project):
    """
    When no individual analysis has been done (rasters_to_analyze is empty)
    and no configurations are passed, no analysis can be made.
    """
    with pytest.raises(ValueError):
        project.analyze_land_suitability()


def test_analyze_land_suitability_full_workflow(temp_project_path, mocker,
                                                cover_config, slope_config,
                                                hand_config):

    mock_get_land_cover_data = mocker.patch.object(
        DataDownloader, "get_land_cover_data", return_value='mocked value')

    project = Project(project_name="Corrientes2",
                      project_year=2025,
                      aoi_path=aoi_path_out,
                      protected_areas_path=protected_path,
                      administrative_borders_path=borders_path,
                      project_dir=temp_project_path,
                      data_dir=data_path_out)

    result = project.analyze_land_suitability(cover_config=cover_config,
                                              slope_config=slope_config,
                                              hand_config=hand_config,
                                              land_checks=False,
                                              )


    # for year 2025 there is no data file available
    assert mock_get_land_cover_data.call_count == 1

    assert temp_project_path.joinpath("results",
                                      "remaining_land.geojson"
                                      ).is_file()
    assert temp_project_path.joinpath("results",
                                      "classified_land.tif"
                                      ).is_file()

    assert isinstance(result, Stats)

def test_project_year_type():

    with pytest.raises(TypeError):
        Project(project_name="nice_project",
                project_year="2025",
                aoi_path=aoi_path_out)
