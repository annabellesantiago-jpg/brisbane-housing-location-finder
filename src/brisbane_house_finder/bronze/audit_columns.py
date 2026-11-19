"""
Add audit columns to Bronze dataframes
Audit columns will record where each row came from and which run loaded it
"""

import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as f

logger = logging.getLogger(__name__)


def add_audit_columns(df: DataFrame, run_id: str) -> DataFrame:
    """
    Add 5 bronze audit columns to a dataframe read from landing files.

    Args:
        df: DataFrame read from files under the landing volume.
        run_id: ID of the job run that loads the data.

    Returns:
        The same rows with _source_file, _source_file_modified_at,
        _download_date, _ingested_at and _run_id added.
    """

    # Landing path: .../raw_files/<dataset_id>/<YYYY-MM-DD>/<file-name>

    source_file = f.col("_metadata.file_path")
    path_parts = f.split(source_file, "/")
    date_folder = f.try_element_at(path_parts, f.lit(-2))
    download_date = f.try_to_date(date_folder, "yyyy-MM-dd")
    checked_download_date = f.when(download_date.isNull(),
                                   f.raise_error(f.concat(
                                       f.lit("No valid date folder in the landing path: "),
                                       source_file)),
                                   ).otherwise(download_date)

    return df.withColumns(
        {"_source_file": source_file,
         "_source_file_modified_at": f.col("_metadata.file_modification_time"),
         "_download_date": checked_download_date,
         "_ingested_at": f.current_timestamp(),
         "_run_id": f.lit(run_id),}
    )
