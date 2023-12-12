from http import HTTPStatus
from unittest import mock, main, TestCase
import handler

# TODO: suppress logs on success


class TestRouterDecorator(TestCase):
    def test_router_adds_endpoint(self):
        valid_paths = [
            ("/foo", "GET", "/foo:GET"),
            ("/foo/bar", "post", "/foo/bar:post"),
            ("/foo/{potato1}", "POST", "/foo/{}:POST"),
            ("/foo/{potato2}/bar", "get", "/foo/{}/bar:get"),
            ("/foo/{potato3}/bar/{potato4}", "POST", "/foo/{}/bar/{}:POST"),
        ]

        with mock.patch.dict("handler.api_routes") as mock_api_routes:
            for path, method, expected_key in valid_paths:

                @handler.router(path=path, method=method)
                def dummy_function(request: handler.Request):
                    pass

                self.assertIn(expected_key, mock_api_routes)

    def test_invalid_symbols_in_router(self):
        invalid_path_param = "Invalid path: {path}; ensure path is written as follows '{{<VALID_VARIABLE_NAME>}}'"
        invalid_path = "Invalid path parameter: {path}; ensure the path parameter is a valid str.identifier()"

        invalid_paths = [
            ("/foo{}", invalid_path),
            ("/foo}", invalid_path),
            ("/}foo", invalid_path),
            ("/foo/user{}s", invalid_path),
            ("/foo/{users", invalid_path_param),
            ("/foo/users}", invalid_path),
        ]

        with mock.patch.dict("handler.api_routes"):
            for path, expected_error in invalid_paths:
                with self.assertRaises(ValueError) as error:

                    @handler.router(path=path, method="POST")
                    def dummy_function(request: handler.Request):
                        pass

                self.assertEqual(expected_error.format(path=path), str(error.exception))

    def test_required_content_length_on_write(self):
        data = (
            b"POST /foo HTTP/1.1\r\nHost: localhost:8000\r\nUser-Agent: curl/8.1.2\r\nAccept: */*\r\nContent-Type:"
            b' application/json\r\n\r\n{"message": "hello"}'
        )
        expected_status_code = HTTPStatus.LENGTH_REQUIRED
        expected_response = {"message": "Content-Length header required"}

        with mock.patch.object(handler.Handler, "send_http_response") as mock_send_response:
            mock_request = mock.Mock(recv=mock.Mock(return_value=data))
            handler.Handler(request=mock_request, client_address=None, server=None)

        self.assertTrue(mock_request.recv.called)
        self.assertTrue(mock_send_response.called)
        self.assertEqual(mock_send_response.call_args[0][0], expected_status_code)
        self.assertEqual(mock_send_response.call_args[1].get("json_body"), expected_response)

    def test_no_content_length_on_read(self):
        data = b"GET /foo HTTP/1.1\r\nHost: localhost:8000\r\nUser-Agent: curl/8.1.2\r\nAccept: */*\r\n\r\n"
        expected_status_code = HTTPStatus.OK

        with mock.patch.object(handler, "api_routes") as mock_api_routes:
            route_resp = handler.HTTPResponse(status_code=expected_status_code, body={"message": "arbitrary response"})
            mock_api_routes.get.return_value = mock.Mock(return_value=route_resp)

            with mock.patch.object(handler.Handler, "send_http_response") as mock_send_response:
                mock_request = mock.Mock(recv=mock.Mock(return_value=data))
                handler.Handler(request=mock_request, client_address=None, server=None)

        self.assertTrue(mock_request.recv.called)
        self.assertTrue(mock_send_response.called)
        self.assertEqual(mock_send_response.call_args[0][0], expected_status_code)

    def test_required_content_type(self):
        data = (
            # Method has to be POST or PUT or PATCH
            b"POST /foo HTTP/1.1\r\nHost: localhost:8000\r\nUser-Agent: curl/8.1.2\r\nAccept: */*\r\n"
            b'Content-Length: 20\r\n\r\n{"message": "hello"}'
        )
        expected_status_code = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
        expected_response = {"message": "A content-type of application/json must be provided"}

        with mock.patch.object(handler.Handler, "send_http_response") as mock_send_response:
            mock_request = mock.Mock(recv=mock.Mock(return_value=data))
            handler.Handler(request=mock_request, client_address=None, server=None)

        self.assertTrue(mock_request.recv.called)
        self.assertTrue(mock_send_response.called)
        self.assertEqual(mock_send_response.call_args[0][0], expected_status_code)
        self.assertEqual(mock_send_response.call_args[1].get("json_body"), expected_response)

    def test_required_http_version(self):
        data = b"GET /foo HTTP/2\r\nHost: localhost:8000\r\nUser-Agent: curl/8.1.2\r\nAccept: */*\r\n\r\n"
        expected_status_code = HTTPStatus.HTTP_VERSION_NOT_SUPPORTED
        expected_response = {"message": "Use HTTP/1.1 version"}

        with mock.patch.object(handler.Handler, "send_http_response") as mock_send_response:
            mock_request = mock.Mock(recv=mock.Mock(return_value=data))
            handler.Handler(request=mock_request, client_address=None, server=None)

        self.assertTrue(mock_request.recv.called)
        self.assertTrue(mock_send_response.called)
        self.assertEqual(mock_send_response.call_args[0][0], expected_status_code)
        self.assertEqual(mock_send_response.call_args[1].get("json_body"), expected_response)

    def test_recv_fixed_data_once(self):
        data = (
            b"POST /foo HTTP/1.1\r\nHost: localhost:8000\r\nUser-Agent: curl/8.1.2\r\nAccept: */*\r\nContent-Type: "
            b'application/json\r\nContent-Length: 122\r\n\r\n{"message": "hello", "name": "test", "age": 30, "my_bool":'
            b' true, "my_not_bool": false, "is_null": null, "my_list": [1, 2,]'
        )
        length_first_call = handler.RECV_SIZE

        with mock.patch.object(handler.Handler, "receive_fixed_data") as mock_recv_data:
            mock_recv_data.return_value = data
            handler.Handler(request=mock.Mock(), client_address=None, server=None)

        mock_recv_data.assert_called_once()
        self.assertEqual(mock_recv_data.call_args_list[0][0][0], length_first_call)

    def test_recv_fixed_data_twice(self):
        data = (
            "POST /foo HTTP/1.1\r\nHost: localhost:8000\r\nUser-Agent: curl/8.1.2\r\nAccept: */*\r\n"
            'Content-Type: application/json\r\nContent-Length: 636\r\n\r\n{"message": "hello", "name": '
            '"test", "age": 30, "my_bool": true, "my_not_bool": false, "is_null": null, "my_list": [1, 2, '
        )
        _, *_, body1 = data.split("\n")
        body2 = (
            '3], "is_dict": {"a": 1, "b": 2}, "is_nested": {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": '
            '{"i": {"j": {"k": {"l": {"m": {"n": {"o": {"p": {"q": {"r": {"s": {"t": {"u": {"v": {"w": {"x": '
            '{"y": {"z": {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": {"k": {"l": {"m": {"n": '
            '{"o": {"p": {"q": {"r": {"s": {"t": {"u": {"v": {"w": {"x": {"y": {"z, "a": {"b": {"c": {"d": {"e": '
            '{"f": {"g": {"h": {"i": {"j": {"k": {"l": {"m": {"n": {"o": {"p": {"q": {"r": {"s": {"t": {"u": {"v": '
            '{"w": {"x": {"y": {"z"}}}}'
        )
        length_first_call = handler.RECV_SIZE
        length_sec_call = len(body1 + body2) - len(body1)

        def side_effect(*args, **kwargs):
            if side_effect.counter == 0:
                side_effect.counter += 1
                return data.encode("utf-8")
            return body2.encode("utf-8")

        side_effect.counter = 0

        with mock.patch.object(handler.Handler, "receive_fixed_data") as mock_recv_data:
            mock_recv_data.side_effect = side_effect
            mock_request = mock.Mock()
            handler.Handler(request=mock_request, client_address=None, server=None)

        self.assertTrue(mock_recv_data.call_count, 2)
        call1, call2 = mock_recv_data.call_args_list
        self.assertEqual(call1[0][0], length_first_call)
        self.assertEqual(call2[0][0], length_sec_call)


if __name__ == "__main__":
    main()
