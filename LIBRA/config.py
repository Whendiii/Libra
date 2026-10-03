import os
from urllib.parse import quote_plus


class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "libra-development-secret-key"
    )

    MYSQL_USER = os.environ.get(
        "MYSQL_USER",
        "root"
    )

    MYSQL_PASSWORD = os.environ.get(
        "MYSQL_PASSWORD",
        "Libra@2026DB"
    )

    MYSQL_HOST = os.environ.get(
        "MYSQL_HOST",
        "127.0.0.1"
    )

    MYSQL_PORT = os.environ.get(
        "MYSQL_PORT",
        "3306"
    )

    MYSQL_DATABASE = os.environ.get(
        "MYSQL_DATABASE",
        "libra_db"
    )

    ENCODED_PASSWORD = quote_plus(
        MYSQL_PASSWORD
    )

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://"
        f"{MYSQL_USER}:"
        f"{ENCODED_PASSWORD}"
        f"@{MYSQL_HOST}:"
        f"{MYSQL_PORT}/"
        f"{MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False