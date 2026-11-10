import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else "/bin/bash"


class Lifecycle(unittest.TestCase):
    def test_failure_after_replacement_attempts_rollback_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = pathlib.Path(directory) / "trace"
            work = pathlib.Path(directory) / "work"; work.mkdir()
            script = f'source "{(ROOT / "restore.sh").as_posix()}"\n' + r'''
systemctl(){ printf 'systemctl %s\n' "$*" >> "$TRACE"; }
python3(){ printf 'python3 %s\n' "$*" >> "$TRACE"; [[ "$MOCK_FAIL" != yes ]]; }
WORK="$TEST_WORK"; CHANGED=true; STOPPED=true
OLD_UI=true; OLD_VPN=true; OLD_TIMER=true
trap cleanup EXIT
false
'''
            for fail in ("no", "yes"):
                with self.subTest(fail=fail):
                    work.mkdir(exist_ok=True)
                    trace.unlink(missing_ok=True)
                    result = subprocess.run([BASH], input=script, text=True, capture_output=True,
                                            env=dict(os.environ, TRACE=trace.as_posix(), TEST_WORK=work.as_posix(), MOCK_FAIL=fail))
                    self.assertNotEqual(result.returncode, 0)
                    calls = trace.read_text()
                    self.assertIn('replace ' + work.as_posix() + '/previous /', calls)
                    self.assertNotIn('reload ssh', calls)
                    if fail == "no":
                        self.assertIn('start openvpn@server.service', calls)
                        self.assertIn('start openvpn-ui.service', calls)
                    else:
                        self.assertNotIn('start openvpn@server.service', calls)
                        self.assertIn('Retour arriere incomplet', result.stderr)

    def test_activating_crl_is_not_treated_as_inactive(self):
        script = f'source "{(ROOT / "restore.sh").as_posix()}"\n' + '''
systemctl(){ echo activating; }
sleep(){ :; }
wait_crl
'''
        result = subprocess.run([BASH], input=script, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__": unittest.main()
