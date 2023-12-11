from http import HTTPMethod, HTTPStatus
from socketserver import TCPServer

from handler import Handler, Request, logger, router, HTTPResponse


@router(path="/foo", method=HTTPMethod.POST)
def foo(request: Request):
    return HTTPResponse(status_code=HTTPStatus.OK, body={"message": "Hello, World!"})


if __name__ == "__main__":
    TCPServer.allow_reuse_address = True
    TCPServer.allow_reuse_port = True
    with TCPServer(("0.0.0.0", 8000), Handler) as server:
        logger.info("Listening to server on port 8000...")
        server.serve_forever()
