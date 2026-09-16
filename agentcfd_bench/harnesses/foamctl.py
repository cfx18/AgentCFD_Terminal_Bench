"""Public in-sandbox client. Contains no credentials or private task metadata."""

import argparse
import http.client
import json
import socket


class Connection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(60)
        self.sock.connect("/api/native.sock")


def main():
    parser = argparse.ArgumentParser(
        description="Native OpenFOAM execution, logs and final submission"
    )
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("exec", "run"):
        command = sub.add_parser(name)
        command.add_argument("--seconds", type=float)
        command.add_argument("argv", nargs=argparse.REMAINDER)
    for name in ("status", "cancel", "submit"):
        sub.add_parser(name).add_argument("run_id")
    logs = sub.add_parser("logs")
    logs.add_argument("run_id")
    logs.add_argument("--stream", choices=["stdout", "stderr"], default="stdout")
    logs.add_argument("--offset", type=int, default=0)
    logs.add_argument("--size", type=int, default=16000)
    request = vars(parser.parse_args())
    if request.get("argv", [])[:1] == ["--"]:
        request["argv"] = request["argv"][1:]
    conn = Connection("localhost")
    conn.request(
        "POST", "/tools", json.dumps(request), {"Content-Type": "application/json"}
    )
    response = conn.getresponse()
    print(response.read().decode())
    conn.close()
    return 0 if response.status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
