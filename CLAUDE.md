# TouchDesigner Agent

## What This Is
A TCP bridge that lets code agents (Claude Code, etc.) control TouchDesigner remotely — query nodes, write GLSL shaders, check compile errors, and iterate without manual intervention.

## Architecture
- **TD side**: TCP/IP DAT (server, port 7000) + Text DAT with callbacks → receives commands, executes Python in TD, returns JSON
- **Agent side**: `bridge/client.py` → `TDClient` class that sends commands over TCP

## Key Patterns

### Writing GLSL (always use file-based workflow)
**Always create local `.glsl` files** — never write code directly into DATs. This keeps everything in Git and editable outside TD.

```python
# First time: creates {project_dir}/shaders/my_shader.glsl + synced Text DAT in TD
td.setup_shader('my_shader', project_dir='/path/to/td/project', initial_code=glsl_code)

# Later edits: just overwrite the local file — TD auto-reloads via sync
td.write_glsl_file('/path/to/td/project/shaders/my_shader.glsl', updated_code)
```

Shader files go in the **user's project directory**, not in this tool repo.

### Compile Check Loop
```python
td.setup_shader('my_shader', project_dir=project_dir, initial_code=code)
td.execute("op('/project1/glsl1').cook(force=True)")
result = td.glsl_check('/project1/glsl1')
# result["ok"] is True if no errors, result["errors"] has the error string
```

### Querying TD State
```python
td.query("op('/project1/glsl1').par.sizex.val")   # any Python expression
td.list_nodes("/project1")                          # list children
td.node_info("/project1/glsl1")                     # type, family, inputs, errors
```

## File Layout
```
bridge/client.py      — Python client (used by agent)
td-setup/callbacks.py — Paste into TD's Text DAT
```

## Rules
- All communication is localhost TCP (default port 7000, but the user may change it per scene)
- **Before connecting or making any changes, always ask the user which port and which TD scene they're working in.** Multiple scenes may be open at once, each on a different port.
- TD must have the TCP/IP DAT running in Server mode before the agent can connect
- GLSL TOPs reference shader code via Text DATs or File In DATs, not direct file paths
- **Prefer file-based workflow**: use `setup_shader()` to create local files with TD sync, so all code lives in Git
