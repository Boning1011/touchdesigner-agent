# TouchDesigner Agent

## What This Is
A TCP bridge that lets code agents (Claude Code, etc.) control TouchDesigner remotely — query nodes, write GLSL shaders, check compile errors, and iterate without manual intervention.

## Architecture
- **TD side**: TCP/IP DAT (server, port 7000) + Text DAT with callbacks → receives commands, executes Python in TD, returns JSON
- **Agent side**: `bridge/client.py` → `TDClient` class that sends commands over TCP

## Key Patterns

### Writing GLSL
Two approaches:
1. **Direct write**: `td.write_glsl('/project1/glsl1_compute', code)` — writes into a Text DAT directly
2. **File-based**: Write `.glsl` files to `shaders/` dir → File In DAT reads them → GLSL TOP compiles

### Compile Check Loop
```python
td.write_glsl(dat_path, code)
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
shaders/              — External .glsl files (optional)
```

## Rules
- All communication is localhost TCP on port 7000
- TD must have the TCP/IP DAT running in Server mode before the agent can connect
- GLSL TOPs reference shader code via Text DATs or File In DATs, not direct file paths
