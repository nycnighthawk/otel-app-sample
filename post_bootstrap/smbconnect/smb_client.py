from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
from typing import Any, Optional

import yaml
from smbclient import listdir, open_file, register_session, remove
from smbclient.path import isdir


@dataclass
class ShareConfig:
    server: str
    share: str
    directory: str = ""
    username: Optional[str] = None
    password: Optional[str] = None


def _load_config(path: str) -> list[ShareConfig]:
    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    shares = data.get("shares", [])
    if not isinstance(shares, list) or not shares:
        raise ValueError("Config must contain a non-empty 'shares' list")

    out: list[ShareConfig] = []
    for s in shares:
        out.append(
            ShareConfig(
                server=s["server"],
                share=s["share"],
                directory=s.get("directory", "") or "",
                username=s.get("username"),
                password=s.get("password"),
            )
        )
    return out

def smb_join(*parts: str) -> str:
    # Join UNC parts using backslashes, preserving leading \\server\share
    cleaned = []
    for p in parts:
        if p is None:
            continue
        p = str(p)
        if not p:
            continue
        cleaned.append(p.strip("\\/"))
    if not cleaned:
        return ""
    head = cleaned[0]
    # restore UNC prefix if original started with \\ 
    if parts[0].startswith("\\\\"):
        head = "\\\\" + head.lstrip("\\")
    return head + ("\\" + "\\".join(cleaned[1:]) if len(cleaned) > 1 else "")


def _unc_root(server: str, share: str) -> str:
    return rf"\\{server}\{share}"


def _base_dir(sc: ShareConfig) -> str:
    root = _unc_root(sc.server, sc.share)
    return smb_join(root, sc.directory) if sc.directory else root


def _ensure_session(sc: ShareConfig, seen: set[str]) -> None:
    # Sessions are per-server; avoid re-registering for the same server.
    if sc.server in seen:
        return
    register_session(
        sc.server,
        username=sc.username,
        password=sc.password,
    )
    seen.add(sc.server)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config file")
    args = ap.parse_args()

    shares = _load_config(args.config)

    seen_servers: set[str] = set()

    for sc in shares:
        _ensure_session(sc, seen_servers)

        base_dir = _base_dir(sc)
        if not isdir(base_dir):
            print(f"Skipping (not a directory): {base_dir}")
            continue

        for name in listdir(base_dir):
            if not name.lower().endswith(".txt"):
                continue

            txt_path = smb_join(base_dir, name)
            sim_path = txt_path + ".simulation"

            with open_file(txt_path, mode="r", encoding="utf-8") as fd:
                original = fd.read()

            simulation_content = (
                "SIMULATION FILE\n"
                f"source={txt_path}\n"
                f"generated_at={dt.datetime.utcnow().isoformat()}Z\n"
                "\n--- original content ---\n"
                f"{original}\n"
            )

            with open_file(sim_path, mode="w", encoding="utf-8") as fd:
                fd.write(simulation_content)

            remove(txt_path)

            print(f"[{sc.server}] Created: {sim_path}")
            print(f"[{sc.server}] Deleted: {txt_path}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
