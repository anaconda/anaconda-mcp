# Docker

## Prerequisites

### `ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN`

Both build methods (from conda channels and from source) require the `ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN` environment variable to be set. This token grants access to the private Anaconda Cloud conda channel used to install dependencies.

To obtain the token, request access from the Anaconda Cloud organization administrator, then export it in your shell before building:

```bash
export ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=<your-token>
```

The token is passed to the Docker build as a [BuildKit secret](https://docs.docker.com/build/building/secrets/) and is **not** embedded in the final image.

## Building the Image

Build the Docker image with Make or directly with Docker:

### From Conda Channels (Default)

```bash
# Using Make
make docker-build

# Or directly (requires ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN to be set)
docker buildx build \
  --secret id=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN,env=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN \
  -t anaconda-mcp .
```

The image is based on `condaforge/miniforge3` and installs `anaconda-mcp` from the following conda channels: `defaults`, `datalayer`, `anaconda-cloud`, and a private token-based channel.

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

### Streamable HTTP Mode (Default)

```bash
# Using Make
make docker-run

# Or directly with port mapping
docker run -it -p 8000:8000 --rm anaconda-mcp
```

## Claude Desktop Configuration

To use the Dockerized Anaconda MCP Server with Claude Desktop, add the following to your `claude_desktop_config.json`:

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
