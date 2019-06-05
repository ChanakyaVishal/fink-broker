# Copyright 2019 AstroLab Software
# Author: Abhishek Chauhan, Julien Peloton
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

import json
import os
import glob
import shutil

from fink_broker.avroUtils import readschemafromavrofile
from fink_broker.sparkUtils import to_avro, from_avro
from pyspark.sql import DataFrame
from pyspark.sql.functions import struct, col

def get_kafka_df(df : DataFrame, schema_path : str) -> DataFrame:
    """Create and return a df to pubish to Kafka

    For a kafka output the dataframe should have the following columns:
    key: (optional) Using a unique key can prevent reading duplicate data
                    as Kafka supports "at least once" write semantics
                    and might result in duplicate writing
    value: (required)
    topic: (*optional)
    *if a topic field is not present in the dataframe it has to be given
    while writng to kafka

    This routine groups the DataFrame columns to be published to Kafka into
    a StructType column and convert it into avro(binary).
    To be able to decode the sent Kafka messages, the avro schema is stored
    at schema_path which is passed as an argument.

    Parameters
    ----------
    df: DataFrame
        A Spark DataFrame created after reading the science database (HBase)
    schema_path: str
        Path where to store the avro schema required for decoding the
        Kafka messages.

    Examples
    ----------

    """
    # Create a StructType column in the df for distribution.
    # The contents and schema of the df can change over time with
    # changing requirements of Alert redistribution
    # df = df.selectExpr("objectId", "simbadType")

    df_struct = df.select(struct(df.columns).alias("struct"))

    # Convert into avro
    df_kafka = df_struct.select(to_avro("struct").alias("value"))

    # Store the avro schema if it doesn't already exist
    # NOTE:
    #   Ensure to delete the avro schema at schema_path whenever the structure
    #   of the df read from science db or the contents to be distribution needs
    #   to be changed.

    if not os.path.isfile(schema_path):
        # Store the df as an avro file
        path_for_avro = os.path.join(os.environ["PWD"], "flatten_hbase.avro")
        if os.path.exists(path_for_avro):
            shutil.rmtree(path_for_avro)
        df.write.format("avro").save(path_for_avro)

        # Read the avro schema from .avro file
        avro_file = glob.glob(path_for_avro + "/part*")[0]
        avro_schema = readschemafromavrofile(avro_file)

        # Write the schema to a file for decoding Kafka messages
        with open(schema_path, 'w') as f:
            json.dump(avro_schema, f)

        # Remove .avro files and directory
        shutil.rmtree(path_for_avro)

    return df_kafka

def decode_kafka_df(df_kafka: DataFrame, schema_path: str) -> DataFrame:
    """Decode the DataFrame read from Kafka

    The DataFrame read from Kafka contains the following columns:
    key: binary
    value: binary
    topic: string
    partition: int
    offset: long
    timestamp: long

    The value column contains the structured data of the alert encoded into
    avro(binary). This routine creates a Spark DataFrame with a decoded StructType
    column using the avro schema at schema_path.

    Parameters
    ----------
    df_kafka: DataFrame
        A Spark DataFrame created after reading the Kafka Source
    schema_path: str
        Path where the avro schema to decode the Kafka message is stored

    Examples
    ----------

    """
    # Read the avro schema
    with open(schema_path) as f:
        avro_schema = json.dumps(json.load(f))

    # Decode the avro(binary) column
    df = df_kafka.select(from_avro("value", avro_schema).alias("struct"))

    return df
