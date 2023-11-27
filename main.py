from functools import partial
from socketserver import TCPServer, BaseRequestHandler
from psycopg2 import connect
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Handler(BaseRequestHandler):
    def __init__(self, db_conn, request, client_address, server) -> None:
        self.db_conn = db_conn
        super().__init__(request, client_address, server)

    def handle(self):
        cursor = self.db_conn.cursor()
        try:
            self.data = self.request.recv(1024).strip().decode("utf-8")
            logger.info("{} wrote: {}".format(self.client_address[0], self.data))

            response_headers = {
                "Content-Type": "text/html; encoding=utf8",
            }
            response_headers_raw = "".join("%s: %s\n" % (k, v) for k, v in response_headers.items())

            response_proto = "HTTP/1.1"
            response_status = "200"
            response_status_text = "OK"
            r = "%s %s %s %s" % (response_proto, response_status, response_status_text, response_headers_raw)
            self.request.sendall(r.encode(encoding="utf-8"))

            result = cursor.execute("SELECT 1")
            logger.info("Query result: {}".format(result))
        except Exception as e:
            logger.error("Error sending request: {}".format(e))
        finally:
            cursor.close()


if __name__ == "__main__":
    logger.info("Listening to server on port 8000...")
    logger.info("Connecting to psql database...")
    try:
        connection = connect(dbname="postgres", user="Dabu", password="postgres")
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
    except Exception as e:
        logger.error("DB Error: ", e)
    finally:
        cursor.close()
    logger.info("DB connected and ready to accept sessions!")

    handler = partial(Handler, connection)
    server = TCPServer(("0.0.0.0", 8000), handler)
    server.serve_forever()
