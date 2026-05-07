from anaconda_mcp.config import Settings


class TestSetAnacondaDomainValidator:
    def test_defaults_to_production_domain(self, monkeypatch):
        monkeypatch.delenv("ANACONDA_MCP_ENVIRONMENT", raising=False)
        monkeypatch.delenv("ANACONDA_MCP_ANACONDA_DOMAIN", raising=False)
        s = Settings()
        assert s.anaconda_domain == "anaconda.com"

    def test_production_environment_resolves_to_production_domain(self, monkeypatch):
        monkeypatch.setenv("ANACONDA_MCP_ENVIRONMENT", "production")
        monkeypatch.delenv("ANACONDA_MCP_ANACONDA_DOMAIN", raising=False)
        s = Settings()
        assert s.anaconda_domain == "anaconda.com"

    def test_staging_environment_resolves_to_staging_domain(self, monkeypatch):
        monkeypatch.setenv("ANACONDA_MCP_ENVIRONMENT", "staging")
        monkeypatch.delenv("ANACONDA_MCP_ANACONDA_DOMAIN", raising=False)
        s = Settings()
        assert s.anaconda_domain == "stage.anaconda.com"

    def test_explicit_domain_overrides_environment(self, monkeypatch):
        monkeypatch.setenv("ANACONDA_MCP_ENVIRONMENT", "staging")
        monkeypatch.setenv("ANACONDA_MCP_ANACONDA_DOMAIN", "custom.example.com")
        s = Settings()
        assert s.anaconda_domain == "custom.example.com"

    def test_unknown_environment_falls_back_to_production_domain(self, monkeypatch):
        monkeypatch.setenv("ANACONDA_MCP_ENVIRONMENT", "unknown")
        monkeypatch.delenv("ANACONDA_MCP_ANACONDA_DOMAIN", raising=False)
        s = Settings()
        assert s.anaconda_domain == "anaconda.com"

    def test_extra_env_vars_do_not_raise(self, monkeypatch):
        """Regression test for PR #20 — extra prefixed env vars must not crash."""
        monkeypatch.setenv("ANACONDA_MCP_OPENAI_API_KEY", "sk-fake")
        monkeypatch.delenv("ANACONDA_MCP_ANACONDA_DOMAIN", raising=False)
        s = Settings()
        assert s.anaconda_domain == "anaconda.com"
