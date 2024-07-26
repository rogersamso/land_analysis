# Use official image version 14
FROM postgres:16

# Set environment variables for PostGIS
ENV POSTGIS_VERSION 3

# Install PostGIS and h3-pg extension
RUN apt-get update && \
    apt-get install -y \
        postgresql-$PG_MAJOR-postgis-$POSTGIS_VERSION \
        postgresql-$PG_MAJOR-postgis-$POSTGIS_VERSION-scripts \
        git \
	wget \
        build-essential \
        cmake \
        postgresql-server-dev-$PG_MAJOR

# Install h3-pg extension
RUN cd / && \
    git clone https://github.com/zachasme/h3-pg && \
    cd h3-pg && \
    mkdir build && \
    cd build && \
    cmake .. && \
    make && \
    make install

# Clean up
RUN apt-get remove -y wget build-essential cmake git && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /h3-pg

# Add extension to PostgreSQL
RUN echo "CREATE EXTENSION postgis;" >> /docker-entrypoint-initdb.d/init_postgis.sql
RUN echo "CREATE EXTENSION h3;" >> /docker-entrypoint-initdb.d/init_h3.sql

# Expose PostgreSQL port
EXPOSE 5432

