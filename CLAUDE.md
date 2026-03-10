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

## GLSL POP Pitfalls

### Output attributes must be enabled before writing
`P[id] = ...` requires the attribute listed in the node's **Output Attributes** (`par.outputattrs`). If empty, shader gets `undeclared identifier`.
```python
td.execute("op(path).par.outputattrs = 'P'")       # single
td.execute("op(path).par.outputattrs = 'P Cd v'")   # multiple, space-separated
```

### P is vec3, not vec4
`P[id] = vec4(...)` fails with type mismatch. Always `P[id] = vec3(x, y, z);`.

### Float uniforms: use Vectors page, not Constants
**Constants** page passes `int` to the shader. For `float`, use **Vectors** (`vec0name` / `vec0valuex`). Arrives as `vec4` in shader — access with `.x`.
```python
td.execute("op(path).par.vec0name = 'uMyFloat'")
td.execute("op(path).par.vec0valuex.mode = ParMode.EXPRESSION")
td.execute("op(path).par.vec0valuex.expr = 'absTime.seconds % 100'")
```
Shader: `float t = uMyFloat.x;`

### Keep time values small — avoid float precision loss
`absTime.seconds` grows forever. Large values (1000+) × wave frequencies lose sub-frame precision in 32-bit GLSL → visible stuttering. Always mod in the Python expression: `'absTime.seconds % 100'`.

### Never redeclare TD auto-generated uniforms
TD generates `uniform` declarations from parameter pages automatically. Writing `uniform vec4 uTime;` in the shader when a parameter named `uTime` exists → `redefinition` error. Just use the name directly.

### Cleaning up uniform parameters: reset all three fields
Setting sequence count to 0 does NOT clear names or running expressions. Always reset name, mode, and value:
```python
td.execute("op(path).par.vec0name = ''")
td.execute("op(path).par.vec0valuex.mode = ParMode.CONSTANT")
td.execute("op(path).par.vec0valuex = 0")
```

### Minimal POP GLSL template
```glsl
void main() {
    const uint id = TDIndex();
    if(id >= TDNumElements())
        return;
    vec3 inP = TDIn_P().xyz;
    // ... compute ...
    P[id] = vec3(...);
}
```
Built-ins: `TDIndex()`, `TDNumElements()`, `TDIn_P()`, `TDIn_Cd()`, `TDIn_v()`.

## Rules
- All communication is localhost TCP (default port 7000, but the user may change it per scene)
- **Before connecting or making any changes, always ask the user which port and which TD scene they're working in.** Multiple scenes may be open at once, each on a different port.
- TD must have the TCP/IP DAT running in Server mode before the agent can connect
- GLSL TOPs reference shader code via Text DATs or File In DATs, not direct file paths
- **Prefer file-based workflow**: use `setup_shader()` to create local files with TD sync, so all code lives in Git
- **Auto-commit & push the user's TD project repo after changes are verified working.** The TD project lives in its own Git repo (query `project.folder` in TD to find the path). After modifying anything via the bridge (GLSL, parameters, nodes, etc.), automatically `git add` + `git commit` + `git push` in **that TD project repo** — not this tool repo. Do not ask — just do it as part of the workflow.
