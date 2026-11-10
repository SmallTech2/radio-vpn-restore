import gzip
import hashlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tarfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else "/bin/bash"


class ArchiveModes(unittest.TestCase):
    def rescue(self, work, identity=""):
        rescue = work / ("rescue.tar.gz.age" if identity else "rescue.tar.gz")
        code = f'source "{(ROOT / "restore.sh").as_posix()}"\nWORK="$TEST_WORK"\nIDENTITY="$TEST_IDENTITY"\n'
        if os.name == "nt":
            code += 'WORK=$(cygpath -u "$WORK")\n'
        if not identity:
            code += 'age(){ return 99; }\nage-keygen(){ return 99; }\n'
        code += 'create_rescue "$TEST_RESCUE"\n'
        result = subprocess.run([BASH], input=code, text=True, capture_output=True,
                                env=dict(os.environ, TEST_WORK=work.as_posix(), TEST_IDENTITY=str(identity), TEST_RESCUE=rescue.as_posix()))
        self.assertEqual(result.returncode, 0, result.stderr)
        digest = hashlib.sha256(rescue.read_bytes()).hexdigest()
        self.assertEqual(rescue.with_name(rescue.name + ".sha256").read_text().split()[0], digest)
        return rescue

    def test_plain_rescue_without_age(self):
        with tempfile.TemporaryDirectory() as directory:
            work = pathlib.Path(directory)
            (work / "previous").mkdir()
            (work / "previous/state").write_bytes(b"previous state")
            rescue = self.rescue(work)
            with tarfile.open(rescue) as tar:
                self.assertEqual(tar.extractfile("./state").read(), b"previous state")

    def prepare(self, work, archive, identity=""):
        functions = work / "restore-functions.sh"
        functions.write_text((ROOT / "restore.sh").read_text().replace("</dev/tty", '<<< "$TEST_IDENTITY"'))
        code = f'source "{functions.as_posix()}"'
        code += '\nWORK="$TEST_WORK"\npython3(){ "$TEST_PYTHON" "$@"; }\n'
        if not identity:
            code += 'read(){ echo forbidden-read > "$WORK/key-asked"; return 99; }\nage(){ echo forbidden-age > "$WORK/age-called"; return 99; }\n'
        code += 'prepare_archive "$TEST_ARCHIVE"\n'
        return subprocess.run([BASH], input=code, text=True, capture_output=True,
                              env=dict(os.environ, TEST_WORK=work.as_posix(), TEST_ARCHIVE=str(archive), TEST_IDENTITY=str(identity), TEST_PYTHON=pathlib.Path(sys.executable).as_posix()))

    def test_plain_detected_by_content_no_key_or_age(self):
        with tempfile.TemporaryDirectory() as directory:
            work = pathlib.Path(directory)
            archive = work / "renamed.backup"
            archive.write_bytes(gzip.compress(b"tar fixture"))
            result = self.prepare(work, archive)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((work / "backup.tar.gz").read_bytes(), archive.read_bytes())
            self.assertFalse((work / "key-asked").exists())
            self.assertFalse((work / "age-called").exists())

    def test_unknown_format_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            work = pathlib.Path(directory)
            archive = work / "invalid.tar.gz"
            archive.write_bytes(b"invalid")
            self.assertNotEqual(self.prepare(work, archive).returncode, 0)
            self.assertFalse((work / "backup.tar.gz").exists())

    @unittest.skipUnless(shutil.which("age"), "Mode age teste dans le job CI avec age")
    def test_encrypted_detection_decryption_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            identity, wrong = folder / "identity", folder / "wrong"
            for key in (identity, wrong):
                subprocess.run(["age-keygen", "-o", str(key)], check=True, capture_output=True)
                key.chmod(0o600)
            recipient = subprocess.check_output(["age-keygen", "-y", str(identity)]).decode().strip()
            plain, encrypted = folder / "plain.tar.gz", folder / "encrypted.backup"
            plain.write_bytes(gzip.compress(b"tar fixture"))
            subprocess.run(["age", "-r", recipient, "-o", str(encrypted), str(plain)], check=True)
            for key, success in ((identity, True), (wrong, False)):
                with self.subTest(success=success):
                    work = folder / (key.name + "-work"); work.mkdir()
                    result = self.prepare(work, encrypted, key)
                    self.assertEqual(result.returncode == 0, success, result.stderr)
                    if success: self.assertEqual((work / "backup.tar.gz").read_bytes(), plain.read_bytes())
            data = bytearray(encrypted.read_bytes()); data[-1] ^= 1; encrypted.write_bytes(data)
            corrupt = folder / "corrupt-work"; corrupt.mkdir()
            self.assertNotEqual(self.prepare(corrupt, encrypted, identity).returncode, 0)
            work = folder / "rescue-work"; work.mkdir(); (work / "previous").mkdir()
            (work / "previous/state").write_bytes(b"previous state")
            rescue = self.rescue(work, identity)
            result = subprocess.run(["age", "-d", "-i", str(identity), str(rescue)], capture_output=True)
            self.assertEqual(result.returncode, 0)
            with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:gz") as tar:
                self.assertEqual(tar.extractfile("./state").read(), b"previous state")


if __name__ == "__main__": unittest.main()
