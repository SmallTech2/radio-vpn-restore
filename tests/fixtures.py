"""PKI jetable generee dans un repertoire temporaire, jamais publiee."""
import pathlib
import sqlite3
import subprocess
import sys


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def installation(root, contract):
    for name in contract.TREES:
        (root / name).mkdir(parents=True)
    for name in contract.FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n")
    pki = root / "usr/share/easy-rsa/pki"
    for name in ("private", "issued", "newcerts"):
        (pki / name).mkdir(parents=True, exist_ok=True)
    for name in ("config", "clients", "staticclients"):
        (root / "etc/openvpn" / name).mkdir()
    (root / "etc/openvpn/pki").symlink_to("/usr/share/easy-rsa/pki")
    runtime = root / "opt/openvpn-ui-runtime"
    (runtime / "openvpn-ui").write_text("fixture executable\\n")
    (runtime / "openvpn-ui").chmod(0o755)
    for name in ("static", "views", "swagger"):
        (runtime / name).mkdir()
    (runtime / "conf").mkdir()
    (runtime / "db").mkdir()
    (runtime / "conf/app.conf").write_text('RadioPublicIP = "198.51.100.10"\nRadioVpnNetwork = "10.3.0.0/16"\n')
    with sqlite3.connect(runtime / "db/data.db") as db:
        db.execute("CREATE TABLE ov_client_config (id INTEGER PRIMARY KEY, server_address TEXT)")
        db.execute("INSERT INTO ov_client_config VALUES (1, '198.51.100.10')")
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, password_hash TEXT)")
        db.execute("INSERT INTO users VALUES (1, 'fixture-hash')")
    (root / "etc/radio-vpn-deployed").write_text("release_tag=radio-v2.4\nrelease_source_commit=" + "a"*40 + "\nbinary_source_commit=" + "a"*40 + "\npublic_ip=198.51.100.10\nnetwork=10.3.0.0/16\n")
    run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(pki / "private/ca.key"), "-out", str(pki / "ca.crt"), "-days", "30", "-subj", "/CN=FixtureCA")
    for name, serial in (("server", "01"), ("client", "02"), ("revoked", "03")):
        run("openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", str(pki / f"private/{name}.key"), "-out", str(pki / f"{name}.csr"), "-subj", f"/CN={name}")
        run("openssl", "x509", "-req", "-in", str(pki / f"{name}.csr"), "-CA", str(pki / "ca.crt"), "-CAkey", str(pki / "private/ca.key"), "-set_serial", "0x" + serial, "-days", "20", "-out", str(pki / f"issued/{name}.crt"))
    (pki / "index.txt").write_text("V\t491231235959Z\t\t01\tunknown\t/CN=server\nV\t491231235959Z\t\t02\tunknown\t/CN=client/name=client/LocalIP=10.3.0.10/2FAName=none\nR\t491231235959Z\t240101000000Z\t03\tunknown\t/CN=revoked\n")
    (pki / "serial").write_text("04\n")
    (pki / "openssl.cnf").write_text("[ca]\ndefault_ca=fixture\n[fixture]\ndatabase=" + str(pki / "index.txt") + "\ncertificate=" + str(pki / "ca.crt") + "\nprivate_key=" + str(pki / "private/ca.key") + "\ndefault_md=sha256\ndefault_crl_days=30\n")
    run("openssl", "ca", "-gencrl", "-config", str(pki / "openssl.cnf"), "-out", str(pki / "crl.pem"))
    for name in ("vars", "dh.pem", "ta.key"):
        (pki / name).write_text("fixture\n")
    (root / "etc/openvpn/staticclients/client").write_text("ifconfig-push 10.3.0.10 255.255.0.0\n")
    (root / "etc/openvpn/config/client.conf").write_text("client\nremote 198.51.100.10 1194 udp\n")
    (root / "etc/openvpn/clients/client.ovpn").write_text("client\nremote 198.51.100.10 1194 udp\n<key>\nfixture\n</key>\n")
    (root / "etc/openvpn/server.conf").write_text("dev tun0\ntopology subnet\nclient-to-client\nccd-exclusive\nserver 10.3.0.0 255.255.0.0 nopool\nca /etc/openvpn/pki/ca.crt\ncert /etc/openvpn/pki/issued/server.crt\nkey /etc/openvpn/pki/private/server.key\ncrl-verify /etc/openvpn/pki/crl.pem\ntls-crypt /etc/openvpn/pki/ta.key\ndh /etc/openvpn/pki/dh.pem\nclient-config-dir /etc/openvpn/staticclients\n")
    (pki / "private/ca.key").chmod(0o600)
    (root / "opt/scripts/qrencode").symlink_to("/usr/bin/qrencode")
