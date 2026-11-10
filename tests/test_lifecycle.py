import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else "/bin/bash"


class Lifecycle(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "Simulation Linux de l'assistant complet")
    def test_check_mode_and_incompatibility_never_modify_services_or_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = pathlib.Path(directory)
            home = folder / "home"; (home / ".ssh").mkdir(parents=True)
            (home / ".ssh/authorized_keys").write_text("fixture-public-key\n")
            archive = folder / "backup.tar.gz"; archive.write_bytes(b"fixture")
            # Seuls l'OS, le terminal et les integrations systeme sont simules.
            source = (ROOT / "restore.sh").read_text().replace('. /etc/os-release', 'ID=debian; VERSION_ID=13')
            source = source.replace('</dev/tty', '').replace('$EUID -eq 0 && -t 0', '1 -eq 1').replace('if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi', '')
            functions = folder / "functions.sh"; functions.write_text(source)
            code = f'source "{functions}"\n' + r'''
record(){ printf '%s\n' "$*" >> "$TRACE"; }
systemctl(){ record "systemctl $*"; case "$1" in is-active|cat) return 0;; *) return 99;; esac; }
/usr/sbin/sshd(){ record "sshd $*"; [[ "$1" != -T ]] || echo 'pubkeyauthentication yes'; return 0; }
uname(){ echo x86_64; }
nft(){ record "nft $*"; }
ip(){ echo '1.1.1.1 via 192.0.2.1 src 8.8.4.4'; }
id(){ echo sudo; }
getent(){ printf 'ops:x:1000:1000::%s:/bin/bash\n' "$TEST_HOME"; }
read(){ case "${!#}" in public_ip) public_ip=8.8.4.4;; answer) answer=ops;; *) return 99;; esac; }
prepare_archive(){ record prepare_archive; }
python3(){ record "python3 $*"; case "$2" in
  unpack) mkdir -p "$WORK/restore/payload";;
  compatible) [[ "$FAIL_COMPATIBLE" != yes ]];;
  *) return 0;;
esac; }
install(){ record "FORBIDDEN install $*"; return 99; }
flock(){ record 'FORBIDDEN flock'; return 99; }
logrotate(){ record "logrotate $*"; [[ "$1" == --debug ]]; }
main --check "$TEST_ARCHIVE"
'''
            for failure in ("no", "yes"):
                trace = folder / (failure + ".log")
                result = subprocess.run([BASH], input=code, text=True, capture_output=True,
                                        env=dict(os.environ, TRACE=str(trace), TEST_HOME=str(home),
                                                 TEST_ARCHIVE=str(archive), FAIL_COMPATIBLE=failure, SUDO_USER="ops"))
                self.assertEqual(result.returncode == 0, failure == "no", result.stderr)
                calls = trace.read_text()
                self.assertIn(' compatible ', calls)
                for forbidden in ("FORBIDDEN", "systemctl stop", "systemctl start", "systemctl restart", "systemctl enable", " rollback ", " replace "):
                    self.assertNotIn(forbidden, calls)
                self.assertEqual(archive.read_bytes(), b"fixture")

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
                    self.assertIn('rollback ' + work.as_posix() + '/previous /', calls)
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
