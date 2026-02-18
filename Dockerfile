# syntax=docker/dockerfile:1
# Pinned to an immutable digest for reproducible, tamper-proof builds.
# To update, pull the desired tag and use: docker inspect --format='{{index .RepoDigests 0}}' condaforge/miniforge3:<tag>
FROM condaforge/miniforge3@sha256:40c11cadd6fe3a0e4f60bd10438db470e1934dcc34e703add9796cf1cd7f7169

# Build argument to determine installation method
ARG FROM_SOURCE=false

# Install build dependencies if building from source
RUN if [ "$FROM_SOURCE" = "true" ]; then \
        conda install -y make && \
        conda clean -afy; \
    fi

# Copy source files if building from source
COPY . /tmp/source/
RUN if [ "$FROM_SOURCE" = "false" ]; then \
        rm -rf /tmp/source; \
    fi

# Pre-install dependencies when building from source
RUN --mount=type=secret,id=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN \
    if [ "$FROM_SOURCE" = "true" ]; then \
        echo "Pre-installing dependencies for source build..." && \
        ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=$(cat /run/secrets/ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN) && \
        conda install -y \
            -c defaults \
            -c datalayer \
            -c anaconda-cloud \
            -c https://conda.anaconda.org/t/${ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN}/anaconda-cloud/label/dev \
            environments-mcp-server mcp-compose && \
        conda clean -afy; \
    fi

# Install anaconda-mcp from source
RUN if [ "$FROM_SOURCE" = "true" ]; then \
        echo "Building and installing from source..." && \
        cd /tmp/source && \
        make conda-install && \
        rm -rf /tmp/source; \
    fi

# Install anaconda-mcp from conda channels
RUN --mount=type=secret,id=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN \
    if [ "$FROM_SOURCE" != "true" ]; then \
        echo "Installing from conda channels..." && \
        ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=$(cat /run/secrets/ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN) && \
        conda install -y \
            -c defaults \
            -c datalayer \
            -c anaconda-cloud \
            -c https://conda.anaconda.org/t/${ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN}/anaconda-cloud/label/dev \
            anaconda-mcp && \
        conda clean -afy; \
    fi

# Create a non-root user for runtime (principle of least privilege)
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /opt/conda

# Expose port for HTTP communication
EXPOSE 8000

# Run as non-root user
USER mcp

# The serve command reads its bundled mcp_compose.toml by default,
# and binds to all interfaces for container accessibility.
ENTRYPOINT ["anaconda-mcp"]
CMD ["serve", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
