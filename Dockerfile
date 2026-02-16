FROM condaforge/miniforge3:latest

ARG ANACONDA_MCP_PACKAGE_TOKEN

# Install anaconda-mcp from the default and datalayer conda channels.
RUN conda install -y \
        -c defaults \
        -c datalayer \
        -c anaconda-cloud \
        -c https://conda.anaconda.org/t/${ANACONDA_MCP_PACKAGE_TOKEN}/anaconda-cloud/label/dev \
        anaconda-env-manager \
        anaconda-mcp \
        environments-mcp-server \
        mcp-compose \
    && conda clean -afy

# The serve command reads its bundled mcp_compose.toml by default,
# so no extra --config flag is needed.
ENTRYPOINT ["anaconda-mcp"]
CMD ["serve"]
