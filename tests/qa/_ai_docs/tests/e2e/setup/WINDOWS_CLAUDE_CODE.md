# Anaconda MCP – Windows Quick Start

## Prerequisites
- Claude Desktop for Windows installed
- Anaconda environment with `anaconda-mcp` installed

---

## Step 1 – Generate the config

Open **Anaconda Prompt** and run:

```bash
python -m anaconda_mcp claude-desktop setup-config
```

This creates a config file at:
```
C:\Users\<YourName>\AppData\Roaming\Claude\claude_desktop_config.json
```

---

## Step 2 – Copy config to the correct location

> ⚠️ On Windows, Claude Desktop reads config from a **different location** than where the command writes it.

Find the real config location:
1. Open Claude Desktop
2. Go to **File → Settings → Developer → Edit Config**
3. Note the path — it will look like:
   ```
   C:\Users\<YourName>\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\
   ```

Copy (or overwrite) `claude_desktop_config.json` from `AppData\Roaming\Claude\` into that folder.

The file should look like this (paths will match your username and environment):

```json
{
  "mcpServers": {
    "anaconda-mcp": {
      "command": "C:\\Users\\<YourName>\\anaconda3\\envs\\anaconda-mcp-rc-py311\\python.exe",
      "args": [
        "-m",
        "anaconda_mcp",
        "serve",
        "--delay",
        "5"
      ],
      "env": {
        "ANACONDA_MCP_PYTHON_EXECUTABLE": "C:\\Users\\<YourName>\\anaconda3\\envs\\anaconda-mcp-rc-py311\\python.exe",
        "MCP_COMPOSE_CONFIG_DIR": "C:\\Users\\<YourName>\\anaconda3\\envs\\anaconda-mcp-rc-py311\\Lib\\site-packages\\anaconda_mcp"
      }
    }
  }
}
```

Save the file.

---

## Step 3 – Fully restart Claude Desktop

Closing the window is **not enough** — background processes keep running.

1. Close the Claude Desktop window
2. Open **Task Manager** (`Ctrl + Shift + Esc`)
3. Find and **End Task** on all Claude-related processes
4. Reopen Claude Desktop

---

## Step 4 – Verify it's working

In a new Claude chat, look for the **🔨 hammer icon** in the chat input area.
Click it — you should see Anaconda MCP tools listed.

If the hammer icon doesn't appear:
- Go to **Settings → Developer**
- If the server appears with an **"Open Logs"** button, it failed to start — click it to see the error
