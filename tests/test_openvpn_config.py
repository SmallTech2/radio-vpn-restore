import ipaddress
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from restore_data import require_directive, validate_openvpn

CONFIG = (ROOT / "tests/data/server-generated.conf").read_text()
NETWORK = ipaddress.IPv4Network("10.3.0.0/16")


class OpenVPNConfiguration(unittest.TestCase):
    def test_generated_inline_comment_reproduces_old_rejection(self):
        self.assertIsNone(re.search(r"^server\s+10\.3\.0\.0\s+255\.255\.0\.0\s+nopool\s*$", CONFIG, re.M))
        validate_openvpn(CONFIG, NETWORK)
        # Meme presentation sur la destination : ne pas deplacer le faux negatif.
        require_directive(CONFIG, "server", [("10.3.0.0", "255.255.0.0", "nopool")], label="server.conf de destination")

    def test_whitespace_comments_quotes_and_relative_pki_paths(self):
        text = CONFIG.replace("dev tun0", '  dev\t"tun0" # interface')
        text = text.replace("topology subnet", "\t--topology 'subnet' ; mode")
        text = text.replace("ccd-exclusive", "  'ccd-exclusive' # restriction")
        text = text.replace("ca /etc/openvpn/pki/ca.crt", 'ca "pki/ca.crt" ; CA')
        text = text.replace("/etc/openvpn/pki/", "pki/").replace("\n", "\r\n")
        validate_openvpn(text, NETWORK)

    def test_other_private_networks_keep_their_configured_mask(self):
        for cidr in ("172.20.5.0/24", "192.168.16.0/20"):
            with self.subTest(cidr=cidr):
                network = ipaddress.IPv4Network(cidr)
                text = CONFIG.replace("10.3.0.0 255.255.0.0", f"{network.network_address} {network.netmask}")
                validate_openvpn(text, network)

    def test_missing_or_commented_required_directives_are_named(self):
        for name in ("dev", "topology", "client-to-client", "ccd-exclusive", "server", "crl-verify", "tls-crypt"):
            with self.subTest(name=name):
                text = re.sub(r"^" + re.escape(name) + r"(?=\s|$)", "# " + name, CONFIG, flags=re.M)
                with self.assertRaisesRegex(ValueError, "directive '" + name + "' absente"):
                    validate_openvpn(text, NETWORK)

    def test_wrong_arguments_paths_or_extra_arguments_are_refused(self):
        for before, after, name in (
            ("dev tun0", "dev tap0", "dev"),
            ("topology subnet", "topology net30", "topology"),
            ("client-to-client\n", "client-to-client no\n", "client-to-client"),
            ("ccd-exclusive\n", "ccd-exclusive no\n", "ccd-exclusive"),
            ("server 10.3.0.0", "server 10.4.0.0", "server"),
            ("255.255.0.0", "255.255.255.0", "server"),
            (" nopool ", " ", "server"),
            ("nopool ", "nopool#", "server"),
            ("key /etc/openvpn/pki/private/server.key", "key /etc/shadow", "key"),
            ("tls-crypt /etc/openvpn/pki/ta.key", "tls-crypt /tmp/other.key", "tls-crypt"),
        ):
            with self.subTest(after=after):
                text = CONFIG.replace(before, after)
                self.assertNotEqual(text, CONFIG)
                with self.assertRaisesRegex(ValueError, r"ligne \d+ : directive '" + name + "' incompatible"):
                    validate_openvpn(text, NETWORK)

    def test_conflicting_duplicates_and_custom_binding_are_refused(self):
        for extra, name in (("--dev tap0", "dev"), ("server 10.4.0.0 255.255.0.0 nopool", "server"),
                            ("'tls-crypt' /tmp/other.key", "tls-crypt")):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, "directive '" + name + "' dupliquee aux lignes"):
                    validate_openvpn(CONFIG + "\n" + extra, NETWORK)
        for extra, name in (("  local 198.51.100.10", "local"), ("\t--bind-dev eth0", "bind-dev"),
                            ("'local' 198.51.100.10", "local")):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(ValueError, "directive '" + name + "' non prise en charge"):
                    validate_openvpn(CONFIG + "\n" + extra, NETWORK)


if __name__ == "__main__": unittest.main()
