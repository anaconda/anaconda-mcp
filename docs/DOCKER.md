# Docker

## Building the Image

Build the Docker image with Make or directly with Docker:

### From Conda Channels (Default)

```bash
# Using Make
make docker-build

# Or directly
docker build -t anaconda-mcp .
```

The image is based on `condaforge/miniforge3` and installs `anaconda-mcp` from the `datalayer` and `defaults` conda channels.

### From Source

To build the image from local source code instead of conda channels:

```bash
# Using Make with environment variable  
DOCKER_FROM_SRC=true make docker-build

# Or using the convenience target
make docker-build-from-source

# Or directly with build argument
docker build --build-arg FROM_SOURCE=true -t anaconda-mcp .
```

This approach copies the local source code into the container and builds/installs using `make conda-install`. No external token is required for source builds.

## Running the Container

```bash
# Using Make
make docker-run

# Or directly with port mapping
docker run -p 8000:8000 --rm anaconda-mcp

# For interactive stdio mode (if needed for testing)
docker run -i --rm anaconda-mcp
```

The container starts `anaconda-mcp serve` in HTTP mode by default, binding to `0.0.0.0:8000` for streamable-http communication.

## Claude Desktop Configuration

To use the Dockerized Anaconda MCP Server with Claude Desktop, add the following to your `claude_desktop_config.json`:

### HTTP Mode (Recommended for Containers)

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "docker",
      "args": ["run", "-p", "8000:8000", "--rm", "anaconda-mcp"],
      "transport": "http",
      "url": "http://localhost:8000"
    }
  }
}
```

### Stdio Mode (Alternative)

For stdio communication, use:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "anaconda-mcp", "serve", "--stdio"]
    }
  }
}
```

The HTTP mode is recommended for containerized deployments as it provides better isolation and networking. Make sure the image has been built locally before starting Claude Desktop.
