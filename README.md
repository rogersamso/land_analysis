# Geospatial data exercise

# Exercise 1

The Dockerfile is in the `postgres` folder.

1. Run the following command tu build the image and run the container:

```bash
docker build -t postgres ./postgres
```

```bash
docker run --name posgres_container -e POSTGRES_PASSWORD=my_password -d postgres
```

Change the `my_password` to something else.

2. Log-in as the postgress user:

```bash
docker exec -it container_name psql -U postgres
```

3. Test that everything works as expected:

```bash
CREATE DATABASE testdb;
```

```bash
\c testdb
```

```bash
CREATE EXTENSION postgis;
CREATE EXTENSION h3;
```

Check the installed extensions:
```bash
\dx
```


# Exercise 2

## Details of the implementation

In the first run, the code connects to different STAC clients and collects the required data. If the code is run again, and the previously downloaded datasets cover the new area of interest, the download process is skipped.

For this exercise, I consider a minimum viable area of 100 Ha. If the available area after removing soil outside borders and protected areas is below this value, the user is warned, and execution stops gracefully. Else, the remaining area is updated, and the execution continues.

For the land use types, I considered only Rangeland, Bare ground and Crops. The first two are considered High suitability, whereas Crops are considered Low suitability. The other land covers are discarded.

For the slope, I considered Low suitability slopes those below 1 % and above 5%, Medium suitability between 3% and 5%, and High suitability between 1% and 3%. Similarly, for the height above drainage, I enforced Low suitability for distances below 1 m and above 50 m, Medium suitability from 30 m to 50 m, and High suitability between 1 m and 30 m.

After the land cover, the slope and the hand are classified in low/medium/high suitability, I average the values, and apply a rounding mechanism, which can be selected by the user (default is np.floor).

Along this process, the user is given the option run individual checks (e.g. slope only) or all at once. The user can also choose the desired CRS, where they want to store the results, or whether to store them in a database or on disk (among many others). Regarding this last point, although the logic for storing the outputs in a database is not implemented, with the chosen design pattern, the existing code wouldn't need to be modified (only new code should be added).

Relevant statistics (availabe land, protected areas, min/max/average slope, etc.) are collected during execution, and the results are stored in a json file. The new land classification is stored in a geotif file named `classified_land.tif`.

## Further considerations

Although I included a few tests, if I had to continue with the exercise, I would add MANY more. I would also improve docstrings.

## To run the code:
1. I created two Dockerfiles, one in the app folder and another one in the jupyter folder. The `docker-compose.yml` should spin them up with:

```bash
docker-compose build
```

```bash
docker-compose up -d
```

2. Place any input files (e.g. area of interest, protected areas or administrative borders) in the `inputs` folder, as this folder will be mounted in the app container:

3. Run the app (this is an example run with an aoi that intersects with the border of Brasil):

```bash
docker-compose run app --aoi_file_name area_intersects_border.geojson
```

The container writes the results files to `/app/outputs`, which is mounted in the `outputs` folder in the project directory.

To list all possible command line arguments and their descriptions, run:

```bash
docker-compose run app -h
```

Note that the only mandatory argument is --aoi_file_name, which is the path to file describing the area of interest. The rest are given default values.


4. To plot the results, run the jupyter lab container

```bash
docker-compose run jupyterlab
```

open [this link](http://127.0.0.1:8888/lab) in your browser, and open the plot_results.ipybn notebook


## Optional: running the test suite in a container

```bash
docker-compose run --entrypoint "pytest" app /app/tests
```

# Response to questions

> **1. What kind of aspects would you take into account if you were assigned with the task of implementing this type of analysis at scale?**

I would implement these solutions:
   1. Run the code in a cluster in the cloud (e.g. Google Cloud + Kubernettes) to be able to scale up seamlessly and to do parallel processing
   2. Use databases and create indexes to the geospatial data
   3. Reduce IO operations to the minimum possible
   4. Use lazy loading whenever possible, with libraries such as xarray and Dask
   6. Use efficient data formats (COG, GeoParquet, NetCDF, etc)
   7. Pre-downloaded required datasets for the whole area, and avoid connecting to the resources during code execution
   8. Minimize human intervention along the whole process, by creating automatic reporting mechanisms

> **2. How can you ensure that the output result is consistent over time and responds to the data quality business users expect?**

To ensure consistency, I would start by building a test suite that covers as much code as possible, using results that are known to be correct as test cases.

An additional good practice in this regard would be to create a coverage report, and enforce that no new commits may be pushed to the base code if the test coverage decreases.

I would also make sure that we are using the most recent and highest quality datasets available, and update the old ones if necessary.

I would also implement a data quality assurance mechanism and run quality checks on the data regularly.

To ensure we respond to clients quality expectations, I would first try to get feedback on particular requests, and then try to implement the measures that guarantee their expectations are met.

> **3. If one or more of the input data sources vary with time by their nature (e.g., land use change, deforestation, etc.), how would you approach this challenge? How can we compare the results of the analysis today vs a few months ago?**

I would approched this issue similarly to what I did in the proposed exercise. I would collect the data from this particular area for the last few years (5 or more, depending on legislation), find the adequate land types in each (e.g. no forests, no wetlands, etc), and ensure they are within the province borders and are not protected. Then, with the selection of adequate land types for each year, I would create an intersection for all years, and get the minimum viable area of them all. Then I would cut the last year data with the obtained area, to get the most updated categorization. I would then store this result and tag it with the date of the analysis in a temporal database management system (e.g. PostgreSQL + Postgis), to be able to track changes over time. I would potentially also store intermediate results, such as the rasters for each year, reprojected and cut at the shape of the area of interest, so that this step, which is relativley costly, does not need to be repeated when runing the analysis again.
>
