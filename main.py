import logging
from functools import partial
from socketserver import TCPServer
from socketserver import BaseRequestHandler
from http import HTTPStatus, HTTPMethod

from psycopg2 import connect


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Handler(BaseRequestHandler):
    def __init__(self, api_routes, request, client_address, server) -> None:
        self.api_routes = api_routes
        super().__init__(request, client_address, server)

    def send_http_response(self, http_status: HTTPStatus, route: str, log_level: str, json_body: dict = None) -> str:
        response_headers = {"Content-Type": "application/json; encoding=utf8"}
        response_headers_raw = "".join("%s: %s\n" % (k, v) for k, v in response_headers.items())
        response_proto = "HTTP/1.1"
        response_status = http_status.value
        response_status_text = http_status.name
        response = "%s %s %s %s\n%s" % (response_proto, response_status, response_status_text, response_headers_raw, str(json_body) if json_body else "")
        logger.log(level=log_level, msg=f"{response_proto} {route} {response_status} {response_status_text}")
        self.request.sendall(response.encode(encoding="utf-8"))

    def handle(self):
        self.data = self.request.recv(1024).strip().decode("utf-8")
        request, *headers, data = self.data.split("\n")
        method, route, http_version = request.split(" ")

        # validate http version
        if http_version.strip() != "HTTP/1.1":
            self.send_http_response(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED, route, logging.ERROR, json_body={"message": "Use HTTP/1.1 version"})
            return

        # validate http method
        if method.upper() not in HTTPMethod.__members__:
            self.send_http_response(HTTPStatus.BAD_REQUEST, route, logging.ERROR, json_body={"message": f"Use supported http methods: {', '.join(HTTPMethod.__members__.keys())}"})
            return

        # validate http path
        path = route
        if "?" in route:
            path, query_param = path.split("?") 
        if path not in self.api_routes:
            self.send_http_response(HTTPStatus.UNPROCESSABLE_ENTITY, route, logging.ERROR, json_body={"message": f"Route not found"})
            return

        # TODO: call appropriate route
        
        self.send_http_response(HTTPStatus.OK, route, logging.INFO) 


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

    api_routes = ["/", "/api/v1/health"]
    handler = partial(Handler, api_routes)
    server = TCPServer(("0.0.0.0", 8000), handler)
    logger.info("Listening to server on port 8000...")
    server.serve_forever()
