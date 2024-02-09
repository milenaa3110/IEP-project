from datetime import timedelta
import os

dbUrl = os.environ["DATABASE_URL"]

class Configuration():
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:root@" + dbUrl + "/shopdb"
    JWT_SECRET_KEY = "JWT_SECRET_DEV_KEY"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    SPARK_APP_NAME = "ShopDBSparkApp"

    # MySQL configurations for Spark
    MYSQL_DRIVER = "com.mysql.cj.jdbc.Driver"
    MYSQL_URL = "jdbc:mysql://" + dbUrl + "/shopdb"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "root"