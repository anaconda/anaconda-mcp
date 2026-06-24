.PHONY: build clean fetch-ana sha256

MCPB_CLI ?= npx --yes @anthropic-ai/mcpb@2.1.2
ANA_CLI_VERSION ?=

fetch-ana:
	ANA_CLI_VERSION="$(ANA_CLI_VERSION)" ./scripts/fetch-ana-assets.sh

build: fetch-ana
	$(MCPB_CLI) pack . anaconda-mcp.mcpb

sha256: build
	shasum -a 256 anaconda-mcp.mcpb

clean:
	rm -rf bin anaconda-mcp.mcpb
