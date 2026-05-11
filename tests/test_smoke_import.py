def test_server_module_imports():
    from twikit_mcp.server import build_mcp

    assert callable(build_mcp)
