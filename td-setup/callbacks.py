# TouchDesigner TCP Command Server — Callbacks
#
# SETUP:
#   1. Create a TCP/IP DAT, set Role = Server, Port = 7000
#   2. Create a Text DAT named "callbacks", paste this code
#   3. Set the TCP/IP DAT's "Callbacks DAT" parameter to: callbacks
#
# PROTOCOL:
#   "glsl_check:<path>"  — refresh File In DAT inputs + return compile errors
#   "exec:<code>"        — execute Python statement, return {"ok": true}
#   "<expression>"       — evaluate Python expression, return {"result": "..."}
#   All responses are single-line JSON terminated with \n.

import json


def onReceive(dat, rowIndex, message, bytes, peer):
    message = message.strip()
    if not message:
        return
    try:
        if message.startswith('glsl_check:'):
            path = message.split(':', 1)[1].strip()
            result = _glsl_check(path)
            dat.send(json.dumps(result), terminator='\n')

        elif message.startswith('exec:'):
            code = message.split(':', 1)[1]
            exec(code)
            dat.send('{"ok": true}', terminator='\n')

        else:
            result = eval(message)
            dat.send(json.dumps({"result": str(result)}), terminator='\n')

    except Exception as e:
        dat.send(json.dumps({"error": str(e)}), terminator='\n')


def _glsl_check(glsl_path):
    node = op(glsl_path)
    if node is None:
        return {"error": f"Node not found: {glsl_path}"}

    refreshed = []
    for inp in node.inputs:
        if inp and inp.type == 'filein':
            inp.par.refreshpulse.pulse()
            refreshed.append(inp.path)

    node.cook(force=True)

    errors = node.errors()
    warnings = node.warnings()
    return {
        "refreshed": refreshed,
        "errors": errors if errors else "",
        "warnings": warnings if warnings else "",
        "ok": not errors,
    }


def onConnect(dat, peer):
    pass


def onDisconnect(dat, peer):
    pass
