import hashlib
import io
import json
import os
import pathlib
import sqlite3
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import archive
import restore_data
from fixtures import installation


def pack_fixture(root, output):
    entries = {}
    for p in sorted(root.rglob("*")):
        name = p.relative_to(root).as_posix()
        st = p.lstat()
        entry = dict(mode=st.st_mode & 0o7777, uid=st.st_uid, gid=st.st_gid)
        if p.is_symlink(): entry.update(type="link", target=os.readlink(p))
        elif p.is_dir(): entry.update(type="dir")
        else: entry.update(type="file", sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        entries[name] = entry
    manifest = dict(format=1, deployment=archive.metadata(root), files=entries)
    with tarfile.open(output, "w:gz", dereference=False) as tar:
        info = tarfile.TarInfo("payload"); info.type = tarfile.DIRTYPE; info.mode = 0o700
        tar.addfile(info)
        for p in sorted(root.rglob("*")):
            info = tar.gettarinfo(str(p), "payload/" + p.relative_to(root).as_posix())
            if p.is_file() and not p.is_symlink():
                info.type = tarfile.REGTYPE; info.linkname = ""; info.size = p.stat().st_size
                with p.open("rb") as stream: tar.addfile(info, stream)
            else: tar.addfile(info)
        for name, data in (("manifest.json", json.dumps(manifest).encode()), ("INVENTORY.txt", b"fixture\n")):
            info = tarfile.TarInfo(name); info.mode = 0o600; info.size = len(data)
            if entries:
                info.uid, info.gid = next(iter(entries.values()))["uid"], next(iter(entries.values()))["gid"]
            tar.addfile(info, io.BytesIO(data))


@unittest.skipIf(os.name == "nt", "Integration Linux (permissions et OpenSSL)")
class Restore(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = pathlib.Path(self.temp.name)
        self.root = self.folder / "root"; self.root.mkdir()
        installation(self.root, archive)

    def test_unpack_update_keeps_pki_users_and_fixed_ips(self):
        source = self.folder / "source.tar.gz"
        pack_fixture(self.root, source)
        archive.check(source)
        restore_data.unpack(source, self.folder / "unpacked")
        payload = self.folder / "unpacked/payload"
        before = {p.relative_to(payload).as_posix(): p.read_bytes() for p in (payload / "usr/share/easy-rsa/pki").rglob("*") if p.is_file()}
        restore_data.update(payload, "8.8.4.4", "ops-admin_2")
        restore_data.validate(payload)
        after = {p.relative_to(payload).as_posix(): p.read_bytes() for p in (payload / "usr/share/easy-rsa/pki").rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(os.readlink(payload / "etc/openvpn/pki"), "/usr/share/easy-rsa/pki")
        self.assertEqual((payload / "usr/share/easy-rsa/pki/private/ca.key").stat().st_mode & 0o777, 0o600)
        self.assertIn("remote 8.8.4.4", (payload / "etc/openvpn/clients/client.ovpn").read_text())
        self.assertIn("10.3.0.10", (payload / "etc/openvpn/staticclients/client").read_text())
        with sqlite3.connect(payload / "opt/openvpn-ui-runtime/db/data.db") as db:
            self.assertEqual(db.execute("SELECT server_address FROM ov_client_config").fetchone()[0], "8.8.4.4")
            self.assertEqual(db.execute("SELECT password_hash FROM users").fetchone()[0], "fixture-hash")

    def test_no_ssh_firewall_or_host_key_replacement_and_rollback(self):
        target = self.folder / "target"; target.mkdir()
        installation(target, archive)
        protected = target / "etc/ssh/sshd_config"
        protected.write_text("destination-ssh\n")
        (target / "etc/ssh/ssh_host_ed25519_key").write_text("destination-host-key\n")
        (target / "etc/nftables.conf").write_text("destination-firewall\n")
        restore_data.preserve(target, self.folder / "previous")
        (self.root / "etc/openvpn/config/client.conf").write_text("source\n")
        restore_data.replace(self.root, target)
        self.assertEqual((target / "etc/openvpn/config/client.conf").read_text(), "source\n")
        self.assertEqual(protected.read_text(), "destination-ssh\n")
        self.assertEqual((target / "etc/ssh/ssh_host_ed25519_key").read_text(), "destination-host-key\n")
        self.assertEqual((target / "etc/nftables.conf").read_text(), "destination-firewall\n")
        restore_data.replace(self.folder / "previous", target)
        self.assertIn("remote 198.51.100.10", (target / "etc/openvpn/config/client.conf").read_text())

    def test_reject_wrong_version_ip_and_schema(self):
        for ip in ("::1", "127.0.0.1", "10.0.0.1", "invalid"):
            with self.assertRaises(ValueError): restore_data.update(self.root, ip, "alice")
        with sqlite3.connect(self.root / "opt/openvpn-ui-runtime/db/data.db") as db:
            db.execute("DROP TABLE ov_client_config")
        with self.assertRaises(ValueError): restore_data.update(self.root, "8.8.4.4", "alice")
        p = self.root / "etc/radio-vpn-deployed"; p.write_text(p.read_text().replace("radio-v2.4", "unknown"))
        with self.assertRaises(ValueError): archive.preflight(self.root)

    def test_reject_dangerous_symlink_before_extraction(self):
        config = self.root / "opt/openvpn-ui-runtime/conf/app.conf"
        config.unlink(); config.symlink_to("/etc/shadow")
        source = self.folder / "unsafe.tar.gz"; pack_fixture(self.root, source)
        with self.assertRaises(ValueError): restore_data.unpack(source, self.folder / "extracted")
        self.assertFalse((self.folder / "extracted").exists())


class Orchestration(unittest.TestCase):
    def test_no_install_or_pki_reinitialization_and_fail_closed(self):
        script = (ROOT / "restore.sh").read_text()
        self.assertNotIn("apt-get", script)
        self.assertNotIn("init_all", script)
        self.assertNotIn("systemctl reload ssh", script)
        self.assertIn('replace "$WORK/previous" /', script)
        self.assertLess(script.index('unpack "$WORK/backup.tar.gz"'), script.index('CHANGED=true'))
        self.assertLess(script.index('age -R "$WORK/recipients"'), script.index('CHANGED=true'))


if __name__ == "__main__": unittest.main()
