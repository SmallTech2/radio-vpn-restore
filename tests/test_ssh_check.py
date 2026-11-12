"""Reproduction de SIGPIPE avec une sortie sshd volumineuse, sans serveur SSH."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == "nt", "SIGPIPE et pipelines Linux")
class SshCheck(unittest.TestCase):
    def check(self, authorization="yes", producer_exit=0, legacy=False):
        source = (ROOT / "restore.sh").read_text()
        check = next(line.strip() for line in source.splitlines() if "Acces SSH par cle non autorise." in line)
        if legacy:
            check = check.replace("grep -x 'pubkeyauthentication yes' >/dev/null", "grep -qx 'pubkeyauthentication yes'")
        with tempfile.TemporaryDirectory() as directory:
            writer = pathlib.Path(directory) / "sshd-output.py"
            writer.write_text('''import os, signal, sys
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
os.write(1, ("pubkeyauthentication " + os.environ["AUTHORIZATION"] + "\\n").encode())
chunk = b"other-option value\\n" * 4096
for _ in range(64):
    os.write(1, chunk)
sys.exit(int(os.environ["PRODUCER_EXIT"]))
''')
            script = f'source "{ROOT / "restore.sh"}"\n' + r'''
admin=ops-admin_2
/usr/sbin/sshd(){
  [[ "$*" == "-T -C user=$admin,host=localhost,addr=127.0.0.1" ]] || return 98
  "$TEST_PYTHON" "$TEST_WRITER"
}
die(){ local status=$?; printf 'pipeline_exit=%s : %s\n' "$status" "$*" >&2; exit 1; }
'''+check+'\necho CHECK_OK\n'
            return subprocess.run(["/bin/bash"], input=script, text=True, capture_output=True, timeout=15,
                                  env=dict(os.environ, TEST_PYTHON=sys.executable, TEST_WRITER=str(writer),
                                           AUTHORIZATION=authorization, PRODUCER_EXIT=str(producer_exit)))

    def test_large_output_reproduces_legacy_sigpipe_and_passes_corrected_check(self):
        legacy = self.check(legacy=True)
        self.assertNotEqual(legacy.returncode, 0)
        self.assertIn("pipeline_exit=141", legacy.stderr)
        corrected = self.check()
        self.assertEqual(corrected.returncode, 0, corrected.stderr)
        self.assertIn("CHECK_OK", corrected.stdout)

    def test_denied_key_authentication_still_fails(self):
        result = self.check(authorization="no")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Acces SSH par cle non autorise", result.stderr)

    def test_sshd_error_still_fails_even_when_yes_was_printed(self):
        result = self.check(producer_exit=23)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pipeline_exit=23", result.stderr)


if __name__ == "__main__": unittest.main()
