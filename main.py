from http import HTTPMethod, HTTPStatus
from socketserver import TCPServer

from handler import Handler, Request, logger, router, HTTPResponse
from psycopg2 import connect


@router(path="/foo/{foo_id}/bar/{bar_id}", method=HTTPMethod.POST)
def foo(request: Request):
    return HTTPResponse(status_code=HTTPStatus.OK, body={"message": "Hello, World!"})


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
