# touchdesigner-agent

A TCP bridge that lets AI code agents control [TouchDesigner](https://derivative.ca/) remotely — query nodes, write GLSL shaders, check compile errors, and iterate autonomously.

## Why

TouchDesigner is powerful for real-time visuals, but its node-based workflow can be slow for shader-heavy projects. This bridge lets you describe effects in natural language, have an AI agent write the GLSL, and see results instantly in TD — with automatic compile-error feedback so the agent can self-debug.

## Setup

### 1. TouchDesigner Side (one-time)

In your TD project:

1. **Create a TCP/IP DAT** — set **Role** = `Server`, **Port** = `7000`
2. **Create a Text DAT** — name it `callbacks`, paste the contents of [`td-setup/callbacks.py`](td-setup/callbacks.py)
3. **Link them** — in the TCP/IP DAT's parameters, set **Callbacks DAT** = `callbacks`

The status should show **listening** on port 7000.

### 2. Agent / Python Side

```python
from bridge.client import TDClient

td = TDClient()  # connects to localhost:7000

# Query any TD state
td.query("op('/project1/glsl1').type")          # → 'glsl'
td.list_nodes("/project1")                       # → ['glsl1', 'noise1', ...]

# Write a compute shader directly into a DAT
td.write_glsl("/project1/glsl1_compute", """
void main() {
    const uint id = TDIndex();
    // ...your GLSL here...
    P[id] = vec3(0.0);
}
""")

# Check if it compiles
result = td.glsl_check("/project1/glsl1")
print(result["ok"])      # True / False
print(result["errors"])  # compile error string if any
```

## GLSL Workflow

There are two ways to get shader code into TD:

### Direct Write (recommended for agent workflows)
The agent writes GLSL code directly into a Text DAT via `td.write_glsl()`. Fastest iteration loop — no files on disk.

### File-Based (for version control)
1. Agent writes `.glsl` files to the `shaders/` directory
2. TD uses **File In DAT** nodes pointing to those files
3. Agent calls `td.glsl_check()` which auto-refreshes the File In DATs and returns compile status

## Protocol

The TCP server accepts single-line text commands and returns single-line JSON:

| Command | Description | Response |
|---------|-------------|----------|
| `<expression>` | Evaluate Python expression in TD | `{"result": "..."}` |
| `exec:<code>` | Execute Python statement | `{"ok": true}` |
| `glsl_check:<path>` | Refresh inputs + return compile errors | `{"ok": true/false, "errors": "...", ...}` |

## File Structure

```
bridge/
  client.py           # Python client for external agents
td-setup/
  callbacks.py        # Paste into TD's Text DAT
shaders/              # Optional: external .glsl files
CLAUDE.md             # Agent instructions
```

## License

MIT
