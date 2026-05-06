import matplotlib
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pyspark.sql.datasource import DataSource, DataSourceStreamReader, DataSourceReader, InputPartition
from pyspark.sql.types import StructType
from pyspark.sql import SparkSession, DataFrame
import matplotlib.cm as cm

import requests
from datetime import datetime, timedelta

from sgp4.api import Satrec, jday, SGP4_ERRORS
from astropy.time import Time
from astropy.coordinates import TEME, ITRS
from astropy import units


def teme_to_ecef(rx, ry, rz, jd, fr):
    """Convert TEME to ECEF coordinate system"""
    teme_position = TEME(
        rx * units.km, 
        ry * units.km, 
        rz * units.km, 
        obstime=Time(jd + fr, format="jd")
    )
    ecef_position = teme_position.transform_to(ITRS(obstime=teme_position.obstime))
    return ecef_position.x.value, ecef_position.y.value, ecef_position.z.value

class SatelliteDataSourceReader(DataSourceReader):
    """Batch reader for satellite TLE data."""
    def __init__(self, schema: StructType, options: dict):
        self.options = options
        self.norad_id = options.get("norad_id")
        self.size = int(options.get("size", 5))
        self.timedelta = options.get("timedelta", "seconds=1").split("=")
        self.timedelta = {self.timedelta[0]: int(self.timedelta[1])}
        self.api_key = options.get("api_key", "DEMO_KEY")

        # Fetch the TLE data for the given satellite
        tle = self.fetch_tle_data(self.norad_id, self.api_key)
        self.tle_line1 = tle["line1"]
        self.tle_line2 = tle["line2"]
        self.name = tle["name"]
        self.tle_timestamp = tle["date"]
        self.tle_timestamp = datetime.strptime(self.tle_timestamp, "%Y-%m-%dT%H:%M:%S%z") # Example: "2025-04-09T12:28:54+00:00"

    @staticmethod
    def fetch_tle_data(norad_id: str, api_key: str) -> dict:
        headers = {"Accept": "*/*", "User-Agent": "curl"}
        url = f"https://tle.ivanstanojevic.me/api/tle/{norad_id}"
        response = requests.get(url, headers=headers, params={"api_key": api_key})
        response.raise_for_status()
        return response.json()
    
    def read(self, partition):
        # Note: library imports must be within the method.
        from sgp4.api import Satrec, jday, SGP4_ERRORS
        from datetime import datetime, timedelta

        satellite = Satrec.twoline2rv(
            self.tle_line1,
            self.tle_line2
        )

        for i in range(self.size):
            ts = datetime.now() + (timedelta(**self.timedelta) * i)
            jd, fr = jday(
                ts.year,
                ts.month,
                ts.day,
                ts.hour,
                ts.minute,
                ts.second,
            )

            e, r, v = satellite.sgp4(jd, fr)
            if e != 0:
                e = SGP4_ERRORS.get(e, 'Unknown error')
            r = {"x": r[0], "y": r[1], "z": r[2]}
            v = {"x": v[0], "y": v[1], "z": v[2]}
            yield (ts, r, v, e, self.norad_id, self.name, self.tle_timestamp,self.tle_line1, self.tle_line2, jd, fr)

class SatellitePartition(InputPartition):
    """A partition for satellite TLE data."""
    def __init__(self, norad_id: str, name: str,tle_line1: str, tle_line2: str, tle_timestamp: datetime, size: int):
        self.norad_id = norad_id
        self.name = name
        self.tle_line1 = tle_line1
        self.tle_line2 = tle_line2
        self.tle_timestamp = tle_timestamp
        self.size = size

class SatelliteStreamReader(DataSourceStreamReader):
    """A stream reader for satellite TLE data."""
    def __init__(self, schema: StructType, options: dict):
        self.norad_id = options.get("norad_id").split(",")
        self.size = int(options.get("size", 5))
        self.timedelta = options.get("timedelta", "seconds=1").split("=")
        self.timedelta = {self.timedelta[0]: int(self.timedelta[1])}
        self.api_key = options.get("api_key", "DEMO_KEY")

    def initialOffset(self):
        """
        Return the initial offset of the streaming data source.
        A new streaming query starts reading data from the initial offset.
        If Spark is restarting an existing query, it will restart from the check-pointed offset
        rather than the initial one.

        Returns
        -------
        dict
            A dict or recursive dict whose key and value are primitive types, which includes
            Integer, String and Boolean.
        """
        return {}
    
    def latestOffset(self) -> dict:
        """
        Returns the most recent offset available.

        Returns
        -------
        dict
            A dict or recursive dict whose key and value are primitive types, which includes
            Integer, String and Boolean.
        """
        # Fetch the TLE data for each of the given satellites
        offsets = {}
        for norad_id in self.norad_id:
            tle = SatelliteDataSourceReader.fetch_tle_data(norad_id, self.api_key)
            tle_line1 = tle["line1"]
            tle_line2 = tle["line2"]
            name = tle["name"]
            tle_timestamp = tle["date"]
            offsets[norad_id] = {"name": name, "tle_line1": tle_line1, "tle_line2": tle_line2, "tle_timestamp": tle_timestamp}
        return offsets

    def partitions(self, start: dict, end: dict):
        partitions = []
        for id, val in end.items():
            if id not in start:
                partitions.append(SatellitePartition(id, val["name"], val["tle_line1"], val["tle_line2"], val["tle_timestamp"], self.size))
            else:
                if start[id]["tle_line1"] != val["tle_line1"] or start[id]["tle_line2"] != val["tle_line2"] or start[id]["tle_timestamp"] != val["tle_timestamp"]:
                    partitions.append(SatellitePartition(id, val["name"], val["tle_line1"], val["tle_line2"], val["tle_timestamp"], self.size))
        return partitions

    def read(self, partition: SatellitePartition):
        from datetime import datetime, timedelta
        from sgp4.api import Satrec, jday, SGP4_ERRORS
        
        satellite = Satrec.twoline2rv(
            partition.tle_line1,
            partition.tle_line2
        )

        for i in range(partition.size):
            ts = datetime.now() + (timedelta(**self.timedelta) * i)
            jd, fr = jday(
                ts.year,
                ts.month,
                ts.day,
                ts.hour,
                ts.minute,
                ts.second,
            )

            e, r, v = satellite.sgp4(jd, fr)
            if e != 0:
                e = SGP4_ERRORS.get(e, 'Unknown error')
            r = {"x": r[0], "y": r[1], "z": r[2]}
            v = {"x": v[0], "y": v[1], "z": v[2]}
            yield (
                ts,
                r,
                v,
                e,
                partition.norad_id,
                partition.name,
                datetime.strptime(partition.tle_timestamp, "%Y-%m-%dT%H:%M:%S%z"),
                partition.tle_line1,
                partition.tle_line2,
                jd,
                fr
            )

    def simple_reader(self, start):
        start_idx = start["offset"]

        rows = []

        satellite = Satrec.twoline2rv(
            self.tle_line1,
            self.tle_line2
        )

        for i in range(start_idx, start_idx + self.size):
            ts = datetime.now() + timedelta(seconds=i)
            jd, fr = jday(
                ts.year,
                ts.month,
                ts.day,
                ts.hour,
                ts.minute,
                ts.second,
            )

            e, r, v = satellite.sgp4(jd, fr)
            if e != 0:
                e = SGP4_ERRORS.get(e, 'Unknown error')
            r = {"x": r[0], "y": r[1], "z": r[2]}
            v = {"x": v[0], "y": v[1], "z": v[2]}
            rows.append((
                ts,
                r,
                v,
                e,
                self.norad_id,
                self.name,
                self.tle_timestamp,
                self.tle_line1,
                self.tle_line2,
                jd,
                fr
            ))

        return (iter(rows), {"offset": start_idx + self.size})

class SatelliteDataSource(DataSource):
    """
    A data source for satellite data.
    """

    @classmethod
    def name(cls):
        return "satellite"

    def schema(self):
        return """
            ts TIMESTAMP,
            pos STRUCT<
                x:DOUBLE,
                y:DOUBLE,
                z:DOUBLE
            >,
            velocity STRUCT<
                x:DOUBLE,
                y:DOUBLE,
                z:DOUBLE
            >,
            e STRING,
            norad_id STRING,
            name STRING,
            tle_timestamp TIMESTAMP,
            tle_line1 STRING,
            tle_line2 STRING,
            jd DOUBLE,
            fr DOUBLE
        """

    def streamReader(self, schema: StructType):
        return SatelliteStreamReader(schema, self.options)
    
    def reader(self, schema: StructType):
        return SatelliteDataSourceReader(schema, self.options)


def visualize(df: DataFrame):
    matplotlib.use('Agg')
    pDF = df.toPandas()
    pDF["color_id"] = pd.factorize(pDF["norad_id"])[0]

    # Generate a color map for unique norad_ids
    unique_ids = pDF["norad_id"].unique()
    id_to_color = {
        norad_id: cm.viridis(i / len(unique_ids))
        for i, norad_id in enumerate(unique_ids)
    }

    # Convert TEME to ECEF
    pDF["x_ecef"], pDF["y_ecef"], pDF["z_ecef"] = zip(*pDF.apply(lambda row: teme_to_ecef(
        row["pos"]["x"], row["pos"]["y"], row["pos"]["z"], row["jd"], row["fr"]
    ), axis=1))

    # Plotting
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim([-7000, 7000])
    ax.set_ylim([-7000, 7000])
    ax.set_zlim([-7000, 7000])
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_zlabel('Z (km)')

    # Plot the Earth
    u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
    x = 6371 * np.cos(u) * np.sin(v)
    y = 6371 * np.sin(u) * np.sin(v)
    z = 6371 * np.cos(v)
    ax.plot_wireframe(x, y, z, color='blue', alpha=0.1)

    # Plot the satellites with different colors for each one
    for norad_id, g in pDF.groupby('norad_id'):
        ax.scatter(
            g["x_ecef"], 
            g["y_ecef"], 
            g["z_ecef"], 
            color=id_to_color[norad_id],
            s=10,
            label=f"Satellite {norad_id}"
        )

    ax.legend()
    # plt.show() # Uncomment to display the plot in a notebook
    plt.savefig("satellite_plot.png")


if __name__ == "__main__":
    spark = SparkSession.builder.appName("SatelliteStream").getOrCreate()
    spark.dataSource.register(SatelliteDataSource)

    df = (
        spark
            .readStream
            .format("satellite")
            .option("norad_id", "25544,33499,46362")
            .option("size", "240") # 240 predictions
            .option("timedelta", "minutes=1") # 1-minute predictions. 240 x 1 minute = 240 minutes = 4 hours
            .option("api_key", "DEMO_KEY")
            .load()
    )

    # Processing the stream
    q = (
        df
            .writeStream
            .outputMode("append")
            .trigger(once=True)
            .foreachBatch(lambda df, batch_id: visualize(df))
            .start()
            .awaitTermination()
    )