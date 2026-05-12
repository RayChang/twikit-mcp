def test_map_rate_limit_exception_to_error_payload():
    from tweety_mcp.errors import ErrorCode
    from tweety_mcp.service import map_exception_to_error

    error = map_exception_to_error(Exception("rate limit exceeded"))

    assert error.code == ErrorCode.RATE_LIMITED
    assert error.retryable is True


def test_map_auth_exception_to_auth_expired_error_payload():
    from tweety_mcp.errors import ErrorCode
    from tweety_mcp.service import map_exception_to_error

    error = map_exception_to_error(Exception("401 unauthorized"))

    assert error.code == ErrorCode.AUTH_EXPIRED


def test_map_unknown_exception_to_internal_error_payload():
    from tweety_mcp.errors import ErrorCode
    from tweety_mcp.service import map_exception_to_error

    error = map_exception_to_error(RuntimeError("unexpected"))

    assert error.code == ErrorCode.INTERNAL_ERROR
    assert error.details == {"exception_type": "RuntimeError"}
