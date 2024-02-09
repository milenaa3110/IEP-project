from pyspark.sql import SparkSession,functions as F
from configuration import Configuration
import json
import os


try:
    PRODUCTION = True if ("PRODUCTION" in os.environ) else False
    DATABASE_IP = os.environ["DATABASE_IP"] if ("DATABASE_IP" in os.environ) else "localhost"

    builder = SparkSession.builder.appName("ProductStatistics")

    if (not PRODUCTION):
        builder = builder.master("local[*]") \
            .config(
            "spark.driver.extraClassPath",
            "mysql-connector-j-8.0.33.jar"
        )

    spark = builder.getOrCreate()

    orders_df = spark.read \
            .format("jdbc") \
            .option ( "driver","com.mysql.cj.jdbc.Driver" ) \
            .option("url", Configuration.MYSQL_URL) \
            .option("dbtable", "orders") \
            .option("user", Configuration.MYSQL_USER) \
            .option("password", Configuration.MYSQL_PASSWORD) \
            .load()

    products_df = spark.read \
        .format("jdbc") \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .option("url", Configuration.MYSQL_URL) \
        .option("dbtable", "products") \
        .option("user", Configuration.MYSQL_USER) \
        .option("password", Configuration.MYSQL_PASSWORD) \
        .load()

    product_orders_df = spark.read \
        .format("jdbc") \
        .option("driver", Configuration.MYSQL_DRIVER) \
        .option("url", Configuration.MYSQL_URL) \
        .option("dbtable", "productorders") \
        .option("user", Configuration.MYSQL_USER) \
        .option("password", Configuration.MYSQL_PASSWORD) \
        .load()

    joined_df = products_df \
        .join(product_orders_df, products_df.id == product_orders_df.productId) \
        .join(orders_df, product_orders_df.orderId == orders_df.id)



    result_df = joined_df.groupBy(products_df.name) \
        .agg(
        F.sum(F.when(orders_df.status == 'COMPLETE', product_orders_df.quantity).otherwise(0)).alias('sold'),
        F.sum(F.when(orders_df.status == 'CREATED', product_orders_df.quantity).otherwise(0)).alias('waiting')
    )

    # Create the JSON response
    statistics = result_df.rdd.map(lambda row: {
        "name": row.name,
        "sold": row.sold,
        "waiting": row.waiting
    }).collect()

    result = {"statistics": statistics}
    result_string = json.dumps(result)
    print(f"result={result_string}")
    spark.stop()
except Exception as e:
    print(f"error={str(e)}")
    spark.stop()