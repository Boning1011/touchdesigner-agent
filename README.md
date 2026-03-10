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

All shader code lives as local `.glsl` files in a `shaders/` folder inside your **TD project directory** — synced to TD automatically. This way everything stays in Git and can be edited by any tool (other AIs, text editors, etc.) without opening TD.

### One-command setup
```python
# Creates {project_dir}/shaders/particle_compute.glsl + a synced Text DAT in TD
td.setup_shader('particle_compute', project_dir='C:/Projects/my_td_project', initial_code="""
void main() {
    // your GLSL here
}
""")
```

This does three things:
1. Creates `shaders/particle_compute.glsl` in your project directory
2. Creates a Text DAT (`particle_compute`) in TD pointing to that file
3. Enables **sync mode** — TD auto-reloads whenever the file changes

### Editing later
```python
# Just write to the file — TD picks up changes automatically
td.write_glsl_file('C:/Projects/my_td_project/shaders/particle_compute.glsl', new_code)

# Check if it compiles
result = td.glsl_check('/project1/glsl1')
print(result["ok"], result["errors"])
```

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
CLAUDE.md             # Agent instructions
```

## License

MIT
