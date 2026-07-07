# Server Configuration

`anaconda mcp serve` no longer uses a user-edited server configuration file or a template-rendering startup path. The default server is composed natively in Python:

- vendored conda tools are mounted in-process from `anaconda_mcp.conda_mcp_lite`
- the remote Anaconda search server is proxied with bearer authentication
- `PlatformMiddleware` enforces authentication, Terms of Service, and telemetry
- the server runs over stdio for the launching MCP client

There is no host or port to configure for `serve`, and client setup writes stdio configuration only.

For current runtime configuration, see [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md). For the serve architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).
