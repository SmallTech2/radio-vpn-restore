#!/usr/bin/env python3
"""Operations de fichiers bornees au contrat v1 ; aucune installation ni generation PKI."""
import ipaddress
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time

from archive import check, metadata, preflight, validate_pki

REPLACE = (
    "usr/share/easy-rsa", "etc/openvpn", "opt/openvpn-ui-runtime", "opt/scripts",
    "etc/openvpn-ui.env", "etc/radio-vpn-deployed", "usr/local/sbin/radio-renew-crl",
    "etc/systemd/system/openvpn-ui.service", "etc/systemd/system/radio-renew-crl.service",
    "etc/systemd/system/radio-renew-crl.timer",
)
OPTIONAL_REPLACE = ("etc/logrotate.d/openvpn", "etc/systemd/journald.conf.d/99-radio-limits.conf")


def unpack(archive, destination):
    manifest = check(archive)
    with tarfile.open(archive, "r:gz") as tar:
        size = sum(member.size for member in tar.getmembers() if member.isfile())
    if shutil.disk_usage(destination.parent).free < size * 3 + 64 * 1024 * 1024:
        raise ValueError("Espace libre insuffisant pour extraire et restaurer.")
    # Validation complete avant la premiere extraction. Les liens sont crees en dernier.
    destination.mkdir(mode=0o700)
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        for member in sorted(members, key=lambda m: (m.issym(), len(pathlib.PurePosixPath(m.name).parts))):
            path = destination / member.name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if member.isdir(): path.mkdir(exist_ok=True, mode=0o700)
            elif member.issym(): path.symlink_to(member.linkname)
            else:
                with tar.extractfile(member) as source, path.open("xb") as target:
                    shutil.copyfileobj(source, target)
            os.chown(path, member.uid, member.gid, follow_symlinks=False)
            if not member.issym():
                os.chmod(path, member.mode)
                os.utime(path, (member.mtime, member.mtime))
    preflight(destination / "payload")
    validate_pki(destination / "payload")
    if metadata(destination / "payload") != manifest["deployment"]:
        raise ValueError("Metadonnees du manifeste et du contenu incompatibles.")
    return manifest


def replacement_paths(source, destination):
    for name in REPLACE:
        if not (source / name).exists():
            raise ValueError("Element de restauration absent : " + name)
    # Seuls les chemins constants ci-dessus peuvent etre remplaces ; aucun chemin du manifest.
    for name in REPLACE + OPTIONAL_REPLACE:
        target = destination / name
        for parent in target.parents:
            if parent == destination.parent: break
            if parent.is_symlink(): raise ValueError("Parent symbolique sur la destination.")


def replace(source, destination, rollback=False):
    replacement_paths(source, destination)
    for name in REPLACE + OPTIONAL_REPLACE:
        target = destination / name
        item = source / name
        if not item.exists() and not rollback:
            continue  # Conserver la configuration facultative propre a la destination.
        if target.is_symlink() or target.is_file(): target.unlink()
        elif target.is_dir(): shutil.rmtree(target)
        if not item.exists(): continue  # Retour arriere : retrouver aussi une absence initiale.
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-a", str(item), str(target)], check=True)


def preserve(root, destination):
    destination.mkdir(mode=0o700)
    paths = REPLACE + tuple(name for name in OPTIONAL_REPLACE if (root / name).exists())
    subprocess.run(["cp", "-a", "--parents", *paths, str(destination.resolve())], cwd=root, check=True)


def update(payload, public_ip, admin):
    ip = ipaddress.IPv4Address(public_ip)
    if ip.is_private or ip.is_loopback or ip.is_multicast or ip.is_unspecified or ip.is_reserved or ip.is_link_local:
        raise ValueError("IPv4 publique attendue.")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", admin): raise ValueError("Compte invalide.")
    old = metadata(payload)["public_ip"]
    app = payload / "opt/openvpn-ui-runtime/conf/app.conf"
    text, count = re.subn(r'^RadioPublicIP\s*=.*$', 'RadioPublicIP = "' + public_ip + '"', app.read_text(), flags=re.M)
    if count != 1: raise ValueError("RadioPublicIP absent ou duplique.")
    app.write_text(text)
    db_path = payload / "opt/openvpn-ui-runtime/db/data.db"
    with sqlite3.connect(db_path) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]: raise ValueError("SQLite invalide.")
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        tables = [name for name in tables if name.replace("_", "").lower() == "ovclientconfig"]
        if len(tables) != 1: raise ValueError("Schema UI non pris en charge.")
        table = tables[0]
        if not re.fullmatch(r"[A-Za-z_]+", table): raise ValueError("Table invalide.")
        columns = [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
        matches = [name for name in columns if name.replace("_", "").lower() == "serveraddress"]
        if len(matches) != 1 or not re.fullmatch(r"[A-Za-z_]+", matches[0]): raise ValueError("Colonne UI absente.")
        column = matches[0]
        cursor = db.execute(f'UPDATE "{table}" SET "{column}"=? WHERE "{column}"=?', (public_ip, old))
        if cursor.rowcount < 1: raise ValueError("Adresse UI incoherente avec les metadonnees.")
    paths = [payload / "etc/openvpn/config/client.conf", *(payload / "etc/openvpn/clients").glob("*.ovpn")]
    for path in paths:
        text = path.read_text()
        path.write_text(re.sub(r"^(\s*remote\s+)" + re.escape(old) + r"(?=\s|$)", lambda m: m[1] + public_ip, text, flags=re.M))
    deployment = payload / "etc/radio-vpn-deployed"
    text = re.sub(r"^public_ip=.*$", "public_ip=" + public_ip, deployment.read_text(), flags=re.M)
    text = re.sub(r"^restored_admin_user=.*\n?", "", text, flags=re.M)
    deployment.write_text(text.rstrip() + "\nrestored_admin_user=" + admin + "\n")
    # Aucun UID ni compte Linux de l'ancien VPS n'est importe ; les services UI/PKI tournent root.


def option_pattern(value):
    escaped = re.escape(value)
    return f'''(?:{escaped}|"{escaped}"|'{escaped}')'''


def directive_lines(server, name):
    pattern = r"^[ \t]*(?:" + option_pattern(name) + "|" + option_pattern("--" + name) + r")(?=[ \t]|$)"
    return [(number, line) for number, line in enumerate(server.splitlines(), 1) if re.match(pattern, line)]


def require_directive(server, name, alternatives, label="server.conf"):
    lines = directive_lines(server, name)
    expected = " ou ".join(" ".join((name, *args)) for args in alternatives)
    if not lines:
        raise ValueError(f"{label} : directive '{name}' absente (attendu : {expected}).")
    if len(lines) != 1:
        numbers = ", ".join(str(number) for number, _ in lines)
        raise ValueError(f"{label} : directive '{name}' dupliquee aux lignes {numbers}.")
    number, line = lines[0]
    prefixes = "(?:" + option_pattern(name) + "|" + option_pattern("--" + name) + ")"
    arguments = "(?:" + "|".join("".join(r"[ \t]+" + option_pattern(arg) for arg in args) for args in alternatives) + ")"
    # Les modeles generes ajoutent un commentaire apres la directive server.
    # Le commentaire doit commencer a une frontiere de parametre, pas au milieu d'une valeur.
    if not re.fullmatch(r"[ \t]*" + prefixes + arguments + r"(?:[ \t]+[#;].*)?[ \t]*", line):
        raise ValueError(f"{label} ligne {number} : directive '{name}' incompatible (attendu : {expected}).")


def validate_openvpn(server, network):
    for name, args in {"dev": ("tun0",), "topology": ("subnet",), "client-to-client": (), "ccd-exclusive": (),
                       "server": (str(network.network_address), str(network.netmask), "nopool")}.items():
        require_directive(server, name, [args])
    for name in ("local", "bind-dev"):
        lines = directive_lines(server, name)
        if lines:
            raise ValueError(f"server.conf ligne {lines[0][0]} : directive '{name}' non prise en charge (liaison reseau personnalisee).")
    for name, path in {"ca": "/etc/openvpn/pki/ca.crt", "cert": "/etc/openvpn/pki/issued/server.crt",
                       "key": "/etc/openvpn/pki/private/server.key", "crl-verify": "/etc/openvpn/pki/crl.pem",
                       "tls-crypt": "/etc/openvpn/pki/ta.key", "dh": "/etc/openvpn/pki/dh.pem",
                       "client-config-dir": "/etc/openvpn/staticclients"}.items():
        alternatives = [(path,)]
        if path.startswith("/etc/openvpn/pki/"): alternatives.append((path.removeprefix("/etc/openvpn/"),))
        require_directive(server, name, alternatives)


def validate(payload):
    preflight(payload)
    validate_pki(payload)
    with sqlite3.connect(f"file:{payload / 'opt/openvpn-ui-runtime/db/data.db'}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]: raise ValueError("SQLite invalide.")
    pki = payload / "usr/share/easy-rsa/pki"
    subprocess.run(["openssl", "verify", "-CAfile", str(pki / "ca.crt"), str(pki / "issued/server.crt")], check=True, capture_output=True)
    values = metadata(payload)
    network = ipaddress.IPv4Network(values["network"])
    app = (payload / "opt/openvpn-ui-runtime/conf/app.conf").read_text()
    matches = re.findall(r'^RadioVpnNetwork\s*=\s*"?([^"\s]+)"?\s*$', app, re.M)
    if matches != [str(network)]: raise ValueError("Reseau UI incoherent avec les metadonnees.")
    server = (payload / "etc/openvpn/server.conf").read_text()
    validate_openvpn(server, network)


def compatible(payload, destination):
    preflight(destination)
    validate(payload)
    if metadata(payload)["network"] != metadata(destination)["network"]:
        raise ValueError("Reseaux VPN differents : preparer la destination avec le reseau sauvegarde pour conserver son pare-feu.")
    network = ipaddress.IPv4Network(metadata(destination)["network"])
    server = (destination / "etc/openvpn/server.conf").read_text()
    require_directive(server, "server", [(str(network.network_address), str(network.netmask), "nopool")],
                      label="server.conf de destination")
    replacement_paths(payload, destination)


def routes(payload):
    network = ipaddress.IPv4Network(metadata(payload)["network"])
    rows = json.loads(subprocess.check_output(["ip", "-j", "-4", "route", "show", "table", "all"]))
    for row in rows:
        destination = row.get("dst", "default")
        if destination == "default" or row.get("dev") in ("tun0", "lo"): continue
        if network.overlaps(ipaddress.IPv4Network(destination, strict=False)):
            raise ValueError("Reseau VPN en conflit avec une route du nouveau VPS.")


def tun(payload):
    network = ipaddress.IPv4Network(metadata(payload)["network"])
    for attempt in range(15):
        result = subprocess.run(["ip", "-j", "-4", "address", "show", "dev", "tun0"], capture_output=True)
        if result.returncode == 0:
            for interface in json.loads(result.stdout):
                if any(a.get("local") == str(network.network_address + 1) and a.get("prefixlen") == network.prefixlen for a in interface.get("addr_info", [])):
                    return
        time.sleep(1)
    raise ValueError("Adresse tun0 incorrecte.")


if __name__ == "__main__":
    try:
        action, *args = sys.argv[1:]
        if action == "unpack": unpack(*map(pathlib.Path, args))
        elif action == "update": update(pathlib.Path(args[0]), *args[1:])
        elif action == "preserve": preserve(*map(pathlib.Path, args))
        elif action == "replace": replace(*map(pathlib.Path, args))
        elif action == "rollback": replace(*map(pathlib.Path, args), rollback=True)
        elif action == "compatible": compatible(*map(pathlib.Path, args))
        elif action == "validate": validate(pathlib.Path(args[0]))
        elif action == "routes": routes(pathlib.Path(args[0]))
        elif action == "tun": tun(pathlib.Path(args[0]))
        elif action == "preflight": preflight(pathlib.Path(args[0]))
        else: raise ValueError("Action inconnue.")
    except Exception as error:
        print("ERREUR restauration : " + str(error), file=sys.stderr)
        sys.exit(1)
