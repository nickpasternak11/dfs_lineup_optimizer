import os
from urllib.parse import quote_plus

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "dfs-postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "dfs")
POSTGRES_USER = os.getenv("POSTGRES_USER", "dfs")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "5"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"


def build_database_url() -> str:
    """Return DATABASE_URL if set, otherwise assemble one from the parts."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return (
        f"postgresql+psycopg://{quote_plus(POSTGRES_USER)}:{quote_plus(POSTGRES_PASSWORD)}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


DATABASE_URL = build_database_url()
