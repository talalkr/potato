from socketserver import TCPServer

from handler import Handler, logger, router
from psycopg2 import connect


@router(path="/foo", method="GET")
def foo():
    return True


if __name__ == "__main__":
    logger.info("Verifying a healthy connection to the database...")
    try:
        connection = connect(dbname="postgres", user="Dabu", password="postgres")
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
    except Exception as e:
        logger.error("DB Error: ", e)
    finally:
        cursor.close()
    logger.info("Database connected and ready")

    server = TCPServer(("0.0.0.0", 8000), Handler)
    logger.info("Listening to server on port 8000...")
    server.serve_forever()
