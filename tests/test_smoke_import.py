def test_server_module_imports():
    from twikit_mcp.server import MCPStub, build_mcp

    server = build_mcp()

    assert isinstance(server, MCPStub)
