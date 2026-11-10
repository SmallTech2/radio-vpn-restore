#!/usr/bin/env bash
# Restauration sur un VPS deja prepare par radio-vpn ; aucun appel a init-pki.
set -Eeuo pipefail
umask 077
BASE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WORK=''
CHANGED=false
STOPPED=false
OLD_UI=false
OLD_VPN=false
OLD_TIMER=false
IDENTITY=''
die(){ echo "ERREUR : $*" >&2; exit 1; }
prepare_archive(){
  local archive="$1" format
  IDENTITY=''
  format=$(python3 -c '
import pathlib,sys
with pathlib.Path(sys.argv[1]).open("rb") as stream:
    header=stream.read(32)
if header.startswith(b"\x1f\x8b"): print("gzip")
elif header.startswith(b"age-encryption.org/v1\n"): print("age")
else: sys.exit(1)
' "$archive") || die 'Format inconnu : archive gzip ou age attendue.'
  if [[ "$format" == gzip ]]; then
    cp -- "$archive" "$WORK/backup.tar.gz"
  else
    for tool in age age-keygen; do command -v "$tool" >/dev/null || die 'Archive chiffree : installer age (sudo apt install age).'; done
    read -r -p 'Chemin de la cle privee age de dechiffrement : ' IDENTITY </dev/tty
    [[ -f "$IDENTITY" ]] || die 'Cle age absente.'
    [[ -z $(find "$IDENTITY" -perm /077 -print) ]] || die 'Cle privee age : permissions 0600 requises.'
    age -d -i "$IDENTITY" -o "$WORK/backup.tar.gz" "$archive" 2>"$WORK/decrypt-error" || die 'Dechiffrement refuse : cle, archive ou integrite a verifier.'
  fi
  gzip -t "$WORK/backup.tar.gz"
}
create_rescue(){
  local rescue="$1"
  tar -czf "$WORK/previous.tar.gz" -C "$WORK/previous" .
  gzip -t "$WORK/previous.tar.gz"
  if [[ -n "$IDENTITY" ]]; then
    age-keygen -y "$IDENTITY" > "$WORK/recipients"
    age -R "$WORK/recipients" -o "$WORK/rescue.age" "$WORK/previous.tar.gz"
    mv -- "$WORK/rescue.age" "$rescue"
  else
    mv -- "$WORK/previous.tar.gz" "$rescue"
  fi
  chmod 600 "$rescue"
  (cd "$(dirname "$rescue")"; sha256sum "${rescue##*/}" > "${rescue##*/}.sha256")
}
wait_crl(){
  local state n
  for ((n=0; n<120; n++)); do
    state=$(systemctl show --property=ActiveState --value radio-renew-crl.service) || return 1
    case "$state" in
      inactive|failed) return 0 ;;
      active|activating|reloading|deactivating) sleep 1 ;;
      *) return 1 ;;
    esac
  done
  return 1
}
resume_old(){
  local failed=0
  if $OLD_VPN; then systemctl start openvpn@server.service || failed=1; fi
  if $OLD_UI; then systemctl start openvpn-ui.service || failed=1; fi
  if $OLD_TIMER; then systemctl start radio-renew-crl.timer || failed=1; fi
  return "$failed"
}
cleanup(){
  local code=$?
  trap - EXIT
  if $CHANGED; then
    echo 'Echec : retour aux donnees precedentes ; SSH et nftables ne sont pas modifies.' >&2
    if systemctl stop openvpn-ui.service openvpn@server.service radio-renew-crl.timer &&
       python3 "$BASE/scripts/restore_data.py" replace "$WORK/previous" / && systemctl daemon-reload; then
      resume_old || echo 'Retour des services en echec : utiliser la sauvegarde de secours indiquee.' >&2
    else
      echo 'Retour arriere incomplet : conserver la session SSH et utiliser la sauvegarde de secours.' >&2
    fi
  elif $STOPPED; then
    resume_old || { echo 'Reprise des services a verifier.' >&2; code=1; }
  fi
  [[ -z "$WORK" ]] || rm -rf -- "$WORK"
  exit "$code"
}
main(){
  [[ $EUID -eq 0 && $# == 0 && -t 0 ]] || die 'Usage dans un terminal : sudo bash restore.sh'
  . /etc/os-release
  [[ $ID == debian && $VERSION_ID == 13 && $(uname -m) == x86_64 ]] || die 'Debian 13 AMD64 requis.'
  for tool in python3 openssl ip nft logrotate curl; do command -v "$tool" >/dev/null || die "Commande manquante : $tool. Installer les prerequis du README."; done
  python3 "$BASE/scripts/restore_data.py" preflight /
  /usr/sbin/sshd -t
  systemctl is-active --quiet ssh || die 'SSH inactif.'
  systemctl is-active --quiet nftables || die 'Pare-feu nftables inactif.'
  nft -c -f /etc/nftables.conf
  local archive public_ip detected admin answer home
  read -r -p 'Chemin de la sauvegarde (.tar.gz ou .tar.gz.age) : ' archive </dev/tty
  [[ -f "$archive" && ! -L "$archive" ]] || die 'Archive locale reguliere requise.'
  install -d -m 700 /var/lib/radio-vpn-restore /var/lib/radio-vpn-backup
  exec 9>/var/lib/radio-vpn-backup/backup.lock
  flock -n 9 || die 'Sauvegarde ou restauration deja active.'
  trap cleanup EXIT
  trap 'exit 1' HUP INT TERM
  WORK=$(mktemp -d /var/lib/radio-vpn-restore/.work.XXXXXXXX)
  echo 'Verification de l archive avant remplacement...'
  prepare_archive "$archive"
  python3 "$BASE/scripts/restore_data.py" unpack "$WORK/backup.tar.gz" "$WORK/restore"
  local payload="$WORK/restore/payload"
  detected=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<NF;i++) if($i=="src") {print $(i+1); exit}}') || detected=''
  if ! python3 -c 'import ipaddress,sys; ip=ipaddress.IPv4Address(sys.argv[1]); sys.exit(not ip.is_global)' "$detected" 2>/dev/null; then
    detected=$(curl -4 --fail --silent --show-error --max-time 5 --proto '=https' https://api.ipify.org) || detected=''
  fi
  read -r -p "Nouvelle IPv4 publique${detected:+ [$detected]} : " public_ip </dev/tty
  public_ip=${public_ip:-$detected}
  admin=${SUDO_USER:-}
  if [[ -z "$admin" || "$admin" == root ]]; then
    admin=$(getent group sudo | cut -d: -f4)
    [[ "$admin" != *,* ]] || admin=''
  fi
  read -r -p "Compte administrateur EXISTANT${admin:+ [$admin]} : " answer </dev/tty
  admin=${answer:-$admin}
  [[ "$admin" =~ ^[a-z_][a-z0-9_-]{0,31}$ && "$admin" != root ]] || die 'Nom de compte invalide.'
  id -nG "$admin" | tr ' ' '\n' | grep -qx sudo || die 'Compte sudo existant requis ; creer ce compte avec radio-vpn.'
  home=$(getent passwd "$admin" | cut -d: -f6)
  [[ -s "$home/.ssh/authorized_keys" ]] || die 'Cle SSH du nouveau compte absente.'
  /usr/sbin/sshd -T -C "user=$admin,host=localhost,addr=127.0.0.1" | grep -qx 'pubkeyauthentication yes' || die 'Acces SSH par cle non autorise.'
  python3 "$BASE/scripts/restore_data.py" update "$payload" "$public_ip" "$admin"
  python3 "$BASE/scripts/restore_data.py" validate "$payload"
  python3 "$BASE/scripts/restore_data.py" routes "$payload"
  printf '\nDestination : %s\nCompte conserve : %s\n' "$public_ip" "$admin"
  echo 'La PKI, les clients, les IP fixes et la base UI seront remplaces. Les sessions VPN seront interrompues.'
  echo 'Les acces SSH, cles d hote, mots de passe Linux, nftables et parametres reseau du nouveau VPS sont conserves.'
  echo 'Seuls des profils clients stockes sur le serveur sont adaptes ; les copies deja distribuees restent a modifier si l IP change.'
  read -r -p 'Restaurer ? Taper RESTAURER : ' answer </dev/tty
  [[ "$answer" == RESTAURER ]] || { echo 'Annule : aucun remplacement.'; return 0; }
  systemctl is-active --quiet openvpn-ui.service && OLD_UI=true
  systemctl is-active --quiet openvpn@server.service && OLD_VPN=true
  systemctl is-active --quiet radio-renew-crl.timer && OLD_TIMER=true
  STOPPED=true
  systemctl stop radio-renew-crl.timer
  wait_crl || die 'Renouvellement CRL encore actif ou etat inaccessible.'
  ! pgrep -f '[/]easyrsa( |$)|[/]opt/scripts/(genclient|revoke|renew|rmcert|generate_ca)' >/dev/null || die 'Operation PKI active ; reessayer plus tard.'
  systemctl stop openvpn-ui.service openvpn@server.service
  python3 "$BASE/scripts/restore_data.py" preserve / "$WORK/previous"
  local rescue="/var/lib/radio-vpn-restore/before-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 4).tar.gz"
  [[ -z "$IDENTITY" ]] || rescue+=.age
  create_rescue "$rescue"
  echo "Sauvegarde de secours : $rescue"
  CHANGED=true
  python3 "$BASE/scripts/restore_data.py" replace "$payload" /
  # Gen-crl conserve index.txt, les cles et les certificats ; il remet a jour la validite de la CRL.
  systemctl daemon-reload
  systemctl start radio-renew-crl.service
  python3 "$BASE/scripts/restore_data.py" validate /
  logrotate --debug /etc/logrotate.d/openvpn
  systemctl restart systemd-journald.service
  install -d -m 755 /var/log/openvpn
  systemctl enable --now openvpn@server.service openvpn-ui.service radio-renew-crl.timer logrotate.timer
  systemctl is-active --quiet openvpn@server.service
  systemctl is-active --quiet openvpn-ui.service
  python3 "$BASE/scripts/restore_data.py" tun /
  ss -lun | grep -q ':1194 '
  curl --fail --silent --show-error --retry 5 --retry-connrefused --retry-delay 1 --max-time 10 http://127.0.0.1:8080/login >/dev/null
  /usr/sbin/sshd -t
  systemctl is-active --quiet ssh
  CHANGED=false; STOPPED=false
  echo 'Restauration terminee : VPN et UI actifs, IP tun0 verifiee, CRL renouvelee sans regeneration de certificats.'
  echo 'Verifier un ancien client et un certificat revoque, puis une nouvelle connexion SSH avant de fermer cette session.'
  echo 'Si l IP publique a change : adapter remote dans les profils deja distribues, sans renouveler les certificats.'
  [[ -z "$IDENTITY" ]] || echo 'Retirer la copie temporaire de la cle privee age apres les verifications ; conserver la cle originale hors VPS.'
}
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
