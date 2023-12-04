from unittest import mock, main, TestCase
from handler import Request, router


class TestRouterDecorator(TestCase):
    def test_router_decorator(self):
        valid_paths = [
            ("/foo", "GET", "/foo:GET"),
            ("/foo/bar", "post", "/foo/bar:post"),
            ("/foo/{potato1}", "POST", "/foo/{}:POST"),
            ("/foo/{potato2}/bar", "get", "/foo/{}/bar:get"),
            ("/foo/{potato3}/bar/{potato4}", "POST", "/foo/{}/bar/{}:POST"),
        ]

        with mock.patch.dict("handler.api_routes") as mock_api_routes:
            for path, method, expected_key in valid_paths:

                @router(path=path, method=method)
                def dummy_function(request: Request):
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

                    @router(path=path, method="POST")
                    def dummy_function(request: Request):
                        pass

                self.assertEqual(expected_error.format(path=path), str(error.exception))


if __name__ == "__main__":
    main()
