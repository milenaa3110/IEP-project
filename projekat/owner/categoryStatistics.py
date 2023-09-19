from pyspark.sql import SparkSession,functions as F
from configuration import Configuration
import json
import os


try:
    PRODUCTION = True if ("PRODUCTION" in os.environ) else False
    DATABASE_IP = os.environ["DATABASE_IP"] if ("DATABASE_IP" in os.environ) else "localhost"

    builder = SparkSession.builder.appName("CategoryStatistics")

    if (not PRODUCTION):
        builder = builder.master("local[*]") \
            .config(
            "spark.driver.extraClassPath",
            "mysql-connector-j-8.0.33.jar"
        )

    spark = builder.getOrCreate()

    orders_df = spark.read \
        .format("jdbc") \
        .option("driver", Configuration.MYSQL_DRIVER) \
        .option("url", Configuration.MYSQL_URL) \
        .option("dbtable", "orders") \
        .option("user", Configuration.MYSQL_USER) \
        .option("password", Configuration.MYSQL_PASSWORD) \
        .load()

    products_df = spark.read \
        .format("jdbc") \
        .option("driver", Configuration.MYSQL_DRIVER) \
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
    product_category_df = spark.read \
        .format("jdbc") \
        .option("driver", Configuration.MYSQL_DRIVER) \
        .option("url", Configuration.MYSQL_URL) \
        .option("dbtable", "productcategories") \
        .option("user", Configuration.MYSQL_USER) \
        .option("password", Configuration.MYSQL_PASSWORD) \
        .load()
    categories_df = spark.read \
        .format("jdbc") \
        .option("driver", Configuration.MYSQL_DRIVER) \
        .option("url", Configuration.MYSQL_URL) \
        .option("dbtable", "categories") \
        .option("user", Configuration.MYSQL_USER) \
        .option("password", Configuration.MYSQL_PASSWORD) \
        .load()

    joined_df = product_orders_df.join(products_df, product_orders_df.productId == products_df.id) \
        .join(orders_df, product_orders_df.orderId == orders_df.id)

    delivered_df = joined_df.filter(orders_df.status == "COMPLETE")

    delivered_with_category_df = delivered_df.join(product_category_df,
                                                   delivered_df.productId == product_category_df.productId)

    category_counts = delivered_with_category_df.groupby(product_category_df.categoryId) \
        .agg(F.sum(product_orders_df.quantity).alias("delivered_count"))

    category_counts_with_names = categories_df.join(category_counts,
                                                    categories_df.id == category_counts.categoryId,
                                                    "left_outer")

    category_counts_with_names = category_counts_with_names.fillna({'delivered_count': 0})

    sorted_categories = category_counts_with_names.sort(F.desc("delivered_count"), F.asc("name"))

    result_list = sorted_categories.select("name").rdd.flatMap(lambda x: x).collect()

    response = {
        "statistics": result_list
    }
    result_string = json.dumps(response)
    print(f"result={result_string}")
    spark.stop()
except Exception as e:
    print(f"error={str(e)}")
    spark.stop()