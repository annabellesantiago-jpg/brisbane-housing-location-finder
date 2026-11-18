import pytest


@pytest.mark.spark
def test_spark_session_runs_a_query(spark):
    df = spark.createDataFrame([(1, "Yeerongpilly"), (2, "Toowong")], ["id", "suburb_name"])
    assert df.count() == 2
    assert df.columns == ["id", "suburb_name"]
