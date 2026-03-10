"""TouchDesigner TCP Bridge Client.

Sends Python commands to a TouchDesigner instance running the TCP command
server (TCP/IP DAT + callbacks). Returns parsed JSON responses.

Usage:
    from bridge.client import TDClient
    td = TDClient()
    td.query("op('/project1/glsl1').par.sizex.val")
    td.execute("op('/project1/noise1').par.roughness = 0.5")
    td.glsl_check("/project1/glsl1")
"""

import json
import socket
from pathlib import Path


class TDClient:
    """Lightweight TCP client for TouchDesigner command server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7000, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    # -- low-level --------------------------------------------------------

    def send(self, cmd: str) -> dict:
        """Send a raw command string and return the parsed JSON response."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)
            s.connect((self.host, self.port))
            s.sendall((cmd + "\n").encode("utf-8"))
            chunks = []
            while True:
                try:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    # Check if we received a complete JSON line
                    data = b"".join(chunks).decode("utf-8").strip()
                    if data:
                        try:
                            return json.loads(data)
                        except json.JSONDecodeError:
                            continue  # keep reading
                except socket.timeout:
                    break
            data = b"".join(chunks).decode("utf-8").strip()
            if data:
                return json.loads(data)
            raise TimeoutError("No response from TouchDesigner")

    # -- high-level helpers -----------------------------------------------

    def query(self, expr: str):
        """Evaluate a Python expression in TD and return the result string."""
        resp = self.send(expr)
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("result")

    def execute(self, code: str):
        """Execute a Python statement in TD."""
        resp = self.send("exec:" + code)
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp

    def glsl_check(self, glsl_path: str) -> dict:
        """Refresh File In DATs feeding a GLSL TOP and return compile status.

        Returns dict with keys: refreshed, errors, warnings, ok
        """
        resp = self.send("glsl_check:" + glsl_path)
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp

    def setup_shader(self, name: str, project_dir: str | Path,
                     initial_code: str = "",
                     parent: str = "/project1") -> dict:
        """Create a local .glsl file and a synced Text DAT in TD.

        Does three things automatically:
        1. Creates  {project_dir}/shaders/{name}.glsl  with initial_code
        2. Creates a Text DAT in TD pointing to that file
        3. Enables sync so TD auto-reloads on every file save

        Args:
            name: Shader name (e.g. 'particle_compute'). Used for both
                  the filename and the DAT node name.
            project_dir: Root directory of the user's TD project. The shader
                         file will be created under {project_dir}/shaders/.
            initial_code: GLSL source to write. Defaults to an empty stub.
            parent: TD parent COMP path. Defaults to '/project1'.

        Returns:
            dict with 'file_path' (local) and 'dat_path' (in TD).
        """
        # 1. Create local file in the project's shaders/ folder
        shaders_dir = Path(project_dir) / "shaders"
        shaders_dir.mkdir(parents=True, exist_ok=True)
        file_path = shaders_dir / f"{name}.glsl"
        if not initial_code:
            initial_code = f"// {name}\n"
        file_path.write_text(initial_code, encoding="utf-8")

        # 2. Create Text DAT in TD → point to file → enable sync
        abs_path = str(file_path.resolve()).replace("\\", "/")
        dat_name = name.replace("-", "_").replace(" ", "_")
        self.execute(
            f"n = op('{parent}').create(textDAT, '{dat_name}'); "
            f"n.par.file = '{abs_path}'; "
            f"n.par.syncfile = 1"
        )

        dat_path = f"{parent}/{dat_name}"
        return {"file_path": str(file_path), "dat_path": dat_path}

    def write_glsl(self, dat_path: str, code: str) -> dict:
        """Write GLSL code directly into a Text/DAT node, then return compile info.

        Args:
            dat_path: Path to the DAT holding shader code (e.g. '/project1/glsl1_compute')
            code: The GLSL source code
        """
        escaped = repr(code)
        self.execute(f"op('{dat_path}').text = {escaped}")
        return {"ok": True}

    def write_glsl_file(self, file_path: str | Path, code: str):
        """Write GLSL code to a local file (for File In DAT workflows)."""
        Path(file_path).write_text(code, encoding="utf-8")

    def list_nodes(self, parent: str = "/project1") -> list[str]:
        """List all child node names under a parent COMP."""
        result = self.query(f"[c.name for c in op('{parent}').children]")
        return eval(result)  # result is a string repr of a list

    def node_info(self, path: str) -> dict:
        """Get basic info about a node: type, family, inputs, errors."""
        info = {}
        info["type"] = self.query(f"op('{path}').type")
        info["family"] = self.query(f"op('{path}').family")
        info["inputs"] = self.query(f"[i.name if i else None for i in op('{path}').inputs]")
        info["errors"] = self.query(f"op('{path}').errors()")
        return info
