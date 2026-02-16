# Docker

## Building the Image

Build the Docker image with Make or directly with Docker:

```bash
# Using Make
make docker-build

# Or directly
docker build -t anaconda-mcp .
```

The image is based on `condaforge/miniforge3` and installs `anaconda-mcp` from the `datalayer` and `defaults` conda channels.

## Running the Container

```bash
# Using Make
make docker-run

# Or directly
docker run -i --rm anaconda-mcp
```

The container starts `anaconda-mcp serve` in stdio mode by default.

## Claude Desktop Configuration

To use the Dockerized Anaconda MCP Server with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "anaconda-mcp"]
    }
  }
}
```

Claude Desktop will launch the container as a subprocess and communicate over stdio. Make sure the image has been built locally before starting Claude Desktop.
