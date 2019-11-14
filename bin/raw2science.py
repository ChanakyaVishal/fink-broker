#!/usr/bin/env python
# Copyright 2019 AstroLab Software
# Author: Julien Peloton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Update the (tmp) science database from the raw database alert data.

Step 1: Connect to the raw database
Step 2: Filter alerts based on instrumental or environmental criteria.
Step 3: Run processors (aka science modules) on alerts to generate added value.
Step 4: Push alert data into the tmp science database (parquet)

See http://cdsxmatch.u-strasbg.fr/ for more information on the SIMBAD catalog.
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col
from pyspark.sql.functions import date_format

import argparse
import time
import json

from fink_broker.parser import getargs
from fink_broker.sparkUtils import init_sparksession
from fink_broker.sparkUtils import connect_to_raw_database
from fink_broker.filters import apply_user_defined_filters
from fink_broker.filters import apply_user_defined_processors
from fink_broker.loggingUtils import get_fink_logger, inspect_application

from userfilters.levelone import filter_levelone_names
from userfilters.levelone import processor_levelone_names

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    args = getargs(parser)

    # Initialise Spark session
    spark = init_sparksession(name="raw2science", shuffle_partitions=2)

    # Logger to print useful debug statements
    logger = get_fink_logger(spark.sparkContext.appName, args.log_level)

    # debug statements
    inspect_application(logger)

    df = connect_to_raw_database(
        args.rawdatapath, args.rawdatapath + "/*", latestfirst=False)

    # Apply level one filters
    logger.info(filter_levelone_names)
    df = apply_user_defined_filters(df, filter_levelone_names)

    # Apply level one processors
    logger.info(processor_levelone_names)
    df = apply_user_defined_processors(df, processor_levelone_names)

    # Partition the data hourly
    df_partitionedby = df\
        .withColumn("year", date_format("timestamp", "yyyy"))\
        .withColumn("month", date_format("timestamp", "MM"))\
        .withColumn("day", date_format("timestamp", "dd"))\
        .withColumn("hour", date_format("timestamp", "HH"))

    # Append new rows in the tmp science database
    countquery = df_partitionedby\
        .writeStream\
        .outputMode("append") \
        .format("parquet") \
        .option("checkpointLocation", args.checkpointpath_sci_tmp) \
        .option("path", args.scitmpdatapath)\
        .partitionBy("year", "month", "day", "hour") \
        .start()

    # Keep the Streaming running until something or someone ends it!
    if args.exit_after is not None:
        time.sleep(args.exit_after)
        countquery.stop()
        logger.info("Exiting the raw2science service normally...")
    else:
        # Wait for the end of queries
        spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
