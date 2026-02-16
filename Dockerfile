# syntax=docker/dockerfile:1
FROM condaforge/miniforge3:latest

# Install anaconda-mcp from the default and datalayer conda channels.
# The token for the private anaconda-cloud/label/dev channel is injected
# via a build secret so it never appears in any image layer.
RUN --mount=type=secret,id=ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN \
    ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN=$(cat /run/secrets/ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN) && \
    conda install -y \
        -c defaults \
        -c datalayer \
        -c anaconda-cloud \
        -c https://conda.anaconda.org/t/${ANACONDA_ORG_ANACONDA_CLOUD_CHANNEL_TOKEN}/anaconda-cloud/label/dev \
        anaconda-mcp \
    && conda clean -afy

# Expose port for HTTP communication
EXPOSE 8000

# The serve command reads its bundled mcp_compose.toml by default,
# and binds to all interfaces for container accessibility.
ENTRYPOINT ["anaconda-mcp"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
