import psycopg
from psycopg_pool import ConnectionPool
from psycopg.types.json import Jsonb
from psycopg import sql
import logging
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

logging.getLogger("psycopg").setLevel(logging.DEBUG)
logging.getLogger("psycopg.pool").setLevel(logging.INFO)


def create_connection_pool(
    db_host,
    db_name: str,
    user: str,
    password: str,
    min_size: int = 2,
    max_size: int = 10,
) -> ConnectionPool | None:
    """Opens a psycopg connection pool and returns it for use in other functions"""

    connection_string = (
        f"host={db_host} dbname={db_name} user={user} password={password}"
    )

    try:
        # Create a connection pool
        pool: ConnectionPool[psycopg.Connection[tuple]] = ConnectionPool(
            connection_string,
            min_size=min_size,
            max_size=max_size,
        )
        # Wait for it to be ready, before returning it
        pool.wait()
        return pool
    except Exception as e:
        logging.error(f"Error creating connection pool: {e}")
        return None


def create_table(table: str, cols: dict[str, str]):
    """Create a Table with a given name and column fields"""
    if pool is None:
        raise RuntimeError("Pool not initialized")

    # build each "col_name TYPE" pair, then join with commas
    col_defs = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(dtype))  # type: ignore
        for col, dtype in cols.items()
    )

    query = sql.SQL("CREATE TABLE IF NOT EXISTS {table} ({col_defs})").format(
        table=sql.Identifier(table), col_defs=col_defs
    )

    with pool.connection() as conn:
        conn.execute(query)


def insert_articles(table: str, col: str, articles: list[dict]):
    """Saves articles as Jsonb"""
    if pool is None:
        raise RuntimeError("Pool not initialized")

    query = sql.SQL("INSERT INTO {table} ({col}) VALUES (%s)").format(
        table=sql.Identifier(table), col=sql.Identifier(col)
    )

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, [(Jsonb(a),) for a in articles])


postgres_user = os.getenv("PG_USER", "postgres")
postgres_db = os.getenv("DB_NAME", "postgres")
postgres_host = os.getenv("DB_HOST", "localhost")
postgres_password = os.getenv("PG_PASSWORD", "")

pool = create_connection_pool(
    postgres_host, postgres_db, postgres_user, postgres_password
)

if pool is None:
    exit(1)

if __name__ == "__main__":
    load_dotenv()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            for row in cur:
                print(row)
    pool.close()
