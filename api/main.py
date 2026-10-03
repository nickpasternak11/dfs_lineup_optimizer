import uvicorn
from app.configs.configs import API_WORKERS, SERVER_PORT, log
from dfs_db.config import DB_MAX_OVERFLOW, DB_POOL_SIZE

# Postgres' default max_connections, less headroom for the orchestrator,
# scrapers and psql sessions.
DB_CONNECTION_BUDGET = 80

if __name__ == "__main__":
    connections = API_WORKERS * (DB_POOL_SIZE + DB_MAX_OVERFLOW)
    if connections > DB_CONNECTION_BUDGET:
        log.warning(
            "API_WORKERS=%d x (DB_POOL_SIZE + DB_MAX_OVERFLOW)=%d allows %d DB "
            "connections; lower one of them to stay under Postgres' max_connections",
            API_WORKERS,
            DB_POOL_SIZE + DB_MAX_OVERFLOW,
            connections,
        )
    # Workers are spawned processes, so uvicorn needs an import string rather
    # than the application object.
    uvicorn.run(
        "app.application:application",
        host="0.0.0.0",
        port=SERVER_PORT,
        workers=API_WORKERS,
    )
