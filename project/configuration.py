from datetime import timedelta
import os


dbUrl = os.environ["DATABASE_URL"]

class Configuration():
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://root:root@{dbUrl}/shopdb"