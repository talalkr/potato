import logging
from typing import Callable
from socketserver import BaseRequestHandler
from http import HTTPStatus, HTTPMethod


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


api_routes = {}
PATH_PARAMETER_ID = "{}"


class HTTPException(Exception):
    def __init__(self, status_code: HTTPStatus, message: str) -> None:
        self.status_code = status_code
        self.message = message


class HTTPResponse:
    def __init__(self, status_code: HTTPStatus, body: dict) -> None:
        self.status_code = status_code
        self.body = body


def router(path: str, method: HTTPMethod):
    def inner(func: Callable):
        if "request" not in func.__code__.co_varnames:
            raise TypeError("Endpoint must accept a request object as an argument")

        split_path = path.split("/")

        for i in range(len(split_path)):
            resource = split_path[i]
            if not resource:
                continue
            if resource[:1] != "{":
                if not resource.isidentifier():
                    raise ValueError(
                        f"Invalid path parameter: {path}; ensure the path parameter is a valid str.identifier()"
                    )
                continue
            if resource[-1] != "}" or not resource[1:-1].isidentifier():
                raise ValueError(f"Invalid path: {path}; ensure path is written as follows '{{<VALID_VARIABLE_NAME>}}'")
            # Indicates usage of path parameters in the route
            split_path[i] = PATH_PARAMETER_ID

        merged_path = "/".join(split_path)
        key = f"{merged_path}:{method}"
        api_routes[key] = func

    return inner


class Request:
    def __init__(self, method: HTTPMethod, path: str, params: dict, body: dict) -> None:
        self.method = method
        self.path = path
        self.params = params
        self.body = body


class Handler(BaseRequestHandler):
    def __init__(self, request, client_address, server) -> None:
        self.api_routes = api_routes
        super().__init__(request, client_address, server)

    def send_http_response(self, http_status: HTTPStatus, route: str, log_level: str, json_body: dict = None) -> str:
        response_headers = {"Content-Type": "application/json; encoding=utf8"}
        response_headers_raw = "".join("%s: %s\n" % (k, v) for k, v in response_headers.items())
        response_proto = "HTTP/1.1"
        response_status = http_status.value
        response_status_text = http_status.name
        response = "%s %s %s %s\n%s" % (
            response_proto,
            response_status,
            response_status_text,
            response_headers_raw,
            str(json_body) if json_body else "",
        )
        logger.log(level=log_level, msg=f"{response_proto} {route} {response_status} {response_status_text}")
        self.request.sendall(response.encode(encoding="utf-8"))

    def handle(self):
        self.data = self.request.recv(1024).strip().decode("utf-8")
        request, *headers, body = self.data.split("\n")
        method, route, http_version = request.split(" ")

        # validate http version
        if http_version.strip() != "HTTP/1.1":
            self.send_http_response(
                HTTPStatus.HTTP_VERSION_NOT_SUPPORTED,
                route,
                logging.ERROR,
                json_body={"message": "Use HTTP/1.1 version"},
            )
            return

        # validate http method
        if method not in HTTPMethod.__members__:
            self.send_http_response(
                HTTPStatus.BAD_REQUEST,
                route,
                logging.ERROR,
                json_body={"message": f"Use supported http methods: {', '.join(HTTPMethod.__members__.keys())}"},
            )
            return

        # pull parameters
        query_params = []
        path = ""
        if "?" in route:
            path, query_params = route.split("?")
            query_params = query_params.split("&")

        # replace path parameters with the PATH_PARAMETER_ID identifier
        path_parameters = []
        split_path = route.split("/")
        for i in range(len(split_path)):
            try:
                path_parameters.append(int(split_path[i]))
                split_path[i] = PATH_PARAMETER_ID
            except ValueError:
                continue
        merged_path = "/".join(split_path)

        # call api endpoint
        route_lookup_key = f"{merged_path}:{method}"
        endpoint = self.api_routes.get(route_lookup_key)
        if not endpoint:
            self.send_http_response(
                HTTPStatus.UNPROCESSABLE_ENTITY, route, logging.ERROR, json_body={"message": "Route not found"}
            )
            return

        try:
            request = Request(
                method=method, path=path, params={"path": path_parameters, "query": query_params}, body=body
            )
            result: HTTPResponse = endpoint(request)
            return self.send_http_response(result.status_code, route, logging.INFO, json_body=result.body)
        except HTTPException as e:
            return self.send_http_response(e.status_code, route, logging.ERROR, json_body={"message": e.message})
