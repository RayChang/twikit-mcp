def test_server_module_imports():
    from tweety_mcp.server import MCPStub, build_mcp, main

    server = build_mcp(mcp_factory=lambda name: MCPStub(name=name))

    assert isinstance(server, MCPStub)
    assert callable(main)
