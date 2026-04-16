# Quick Reference: Which Config File to Edit?

## TL;DR

✅ **Edit**: `mcp_compose.toml.template`
❌ **Don't Edit**: `mcp_compose.toml` (it's ignored if template exists)

---

## File Purposes

### `mcp_compose.toml.template` (PRIMARY)

- ✅ **This is what you should edit**
- Contains placeholders like `{{PYTHON_EXECUTABLE}}`
- Rendered at runtime to a temporary file
- Changes take effect immediately on next run

### `mcp_compose.toml` (FALLBACK)

- ⚠️ **Only used if template doesn't exist**
- Any changes will be ignored if template exists
- Kept for backward compatibility
- Don't edit this unless you remove the template

---

## How It Works

```
Startup Process:
┌─────────────────────────────────────┐
│ anaconda-mcp serve                  │
└────────────┬────────────────────────┘
             │
             v
┌─────────────────────────────────────┐
│ Check: Does .template exist?        │
└────────────┬────────────────────────┘
             │
        YES  │  NO
             │
    ┌────────┴────────┐
    │                 │
    v                 v
┌─────────┐    ┌──────────────┐
│ Use     │    │ Use          │
│ .template│   │ .toml        │
│ (render)│    │ (as-is)      │
└─────────┘    └──────────────┘
```

---

## Common Tasks

### Adding a New Server

**✅ Correct:**
Edit `mcp_compose.toml.template`:
```toml
[[servers.proxied.streamable-http]]
name = "my-new-server"
command = ["{{PYTHON_EXECUTABLE}}", "-m", "my_server_module"]
```

**❌ Wrong:**
Don't edit `mcp_compose.toml` - your changes will be ignored!

### Changing Python Path

**Option 1: Environment Variable (Recommended)**
```bash
export ANACONDA_MCP_PYTHON_EXECUTABLE=/custom/path/to/python
python -m anaconda_mcp serve
```

**Option 2: Template Placeholder (Already done)**
The template already uses `{{PYTHON_EXECUTABLE}}` - no need to hardcode paths!

### Changing Port or Other Settings

**✅ Correct:**
Edit `mcp_compose.toml.template`:
```toml
[api]
port = 9000  # Change port here
```

Then restart:
```bash
python -m anaconda_mcp serve
```

---

## Troubleshooting

### "My changes aren't taking effect!"

**Problem**: You edited `mcp_compose.toml` but `mcp_compose.toml.template` exists.

**Solution**: Edit `mcp_compose.toml.template` instead.

### "I want to stop using the template"

**Solution**: Delete `mcp_compose.toml.template`, then edit `mcp_compose.toml`.

But you'll lose:
- Dynamic Python path injection
- Environment variable support
- Automatic sys.executable detection

### "I need a completely custom config"

**Solution 1**: Edit the template with your customizations
```bash
vim src/anaconda_mcp/mcp_compose.toml.template
```

**Solution 2**: Use `--config` flag with a custom file
```bash
python -m anaconda_mcp serve --config /path/to/my/custom.toml
```

Note: Custom config files won't have template rendering unless you create a `.template` file alongside it.

---

## For Package Maintainers

When distributing `anaconda-mcp`:

1. Include both `mcp_compose.toml.template` and `mcp_compose.toml`
2. Template takes precedence
3. Fallback ensures it works even if template is missing
4. Users should be directed to edit the template

Update `pyproject.toml` to include both:
```toml
[tool.hatch.build]
artifacts = [
    "src/anaconda_mcp/mcp_compose.toml",
    "src/anaconda_mcp/mcp_compose.toml.template"
]
```

---

## Summary

| File | Purpose | Should I Edit? |
|------|---------|----------------|
| `mcp_compose.toml.template` | Primary config with placeholders | ✅ YES |
| `mcp_compose.toml` | Fallback (only if template missing) | ❌ NO |

**Remember**: The template is rendered to a **temporary file** at runtime, so your changes to the template take effect immediately without modifying any installed files.
