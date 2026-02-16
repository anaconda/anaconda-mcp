# syntax=docker/dockerfile:1
FROM condaforge/miniforge3:latest

# Install anaconda-mcp from the default and datalayer conda channels.
# The token for the private anaconda-cloud/label/dev channel is injected
# via a build secret so it never appears in any image layer.
RUN --mount=type=secret,id=ANACONDA_MCP_PACKAGE_TOKEN \
    ANACONDA_MCP_PACKAGE_TOKEN=$(cat /run/secrets/ANACONDA_MCP_PACKAGE_TOKEN) && \
    conda install -y \
        -c defaults \
        -c datalayer \
        -c anaconda-cloud \
        -c https://conda.anaconda.org/t/${ANACONDA_MCP_PACKAGE_TOKEN}/anaconda-cloud/label/cko \
        anaconda-mcp \
    && conda clean -afy

# The serve command reads its bundled mcp_compose.toml by default,
# so no extra --config flag is needed.
ENTRYPOINT ["anaconda-mcp"]
CMD ["serve"]
