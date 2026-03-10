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
