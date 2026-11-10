# Erreur et retour arrière

## Avant le remplacement

**Nouveau VPS — administrateur Linux :** si le script refuse l'archive, conserver son message
d'erreur. Vérifier version radio-v2.4, intégrité, espace disque et installation complète :

```bash
sudo cat /etc/radio-vpn-deployed
df -h /var/lib
sudo systemctl is-active ssh nftables openvpn@server.service openvpn-ui.service
sudo /usr/sbin/sshd -t
```

Ne pas contourner un refus de format, de schéma SQLite ou de PKI. Le script ne répare pas
les données et ne doit jamais être remplacé par une réinitialisation de la CA.

## Après le remplacement

Sur erreur interceptable, le script tente de remettre les données précédentes et les
services initialement actifs. Il affiche explicitement un échec de retour arrière.
Il ne remplace pas SSH ou nftables. **Conserver les sessions SSH ouvertes** et la console
de l'hébergeur disponible. Un SIGKILL, une coupure ou un disque défaillant ne peut pas être
traité automatiquement ; les répertoires de travail root privés peuvent alors subsister.

Le script affiche le chemin réel du secours créé sous `/var/lib/radio-vpn-restore`.
Un fichier `before-...tar.gz` représente l'installation **remplacée sur le nouveau VPS**,
pas les clients historiques du NAS. Ce secours n'a pas le manifeste du format de collecte :
ne pas le sélectionner dans `restore.sh` comme s'il s'agissait d'une archive du NAS.

## Secours manuel, seulement si le retour automatique a échoué

Procédure de maintenance pour un opérateur présent, sur **le nouveau VPS**, depuis le
dépôt `radio-vpn-restore`. Ne travailler que sur un secours local de confiance produit par
ce script. Ce bloc arrête le VPN ; il ne modifie pas les accès SSH ou le pare-feu.

**Nouveau VPS — administrateur Linux :** choisir le chemin affiché par le script, puis :

```bash
sudo ls -l /var/lib/radio-vpn-restore
read -r -p 'Chemin absolu du secours local .tar.gz ou .tar.gz.age : ' SECOURS
sudo sh -c 'cd "$(dirname "$1")" && sha256sum -c "$(basename "$1").sha256"' sh "$SECOURS"
RESCUE_DIR=$(sudo mktemp -d /root/radio-vpn-rescue.XXXXXXXX)
if [[ "$SECOURS" == *.age ]]; then
  sudo apt install -y age
  read -r -p 'Chemin de la copie temporaire de clé privée age : ' AGE_KEY
  sudo age -d -i "$AGE_KEY" -o "$RESCUE_DIR/previous.tar.gz" "$SECOURS"
  SECOURS_TAR="$RESCUE_DIR/previous.tar.gz"
else
  SECOURS_TAR="$SECOURS"
fi
sudo gzip -t "$SECOURS_TAR"
sudo mkdir -m 700 "$RESCUE_DIR/state"
sudo tar -xpf "$SECOURS_TAR" --same-owner -C "$RESCUE_DIR/state"
cd "$HOME/radio-vpn-restore"
sudo systemctl stop openvpn-ui.service openvpn@server.service radio-renew-crl.timer radio-renew-crl.service
sudo python3 scripts/restore_data.py replace "$RESCUE_DIR/state" /
sudo systemctl daemon-reload
sudo systemctl start radio-renew-crl.service
sudo systemctl start openvpn@server.service openvpn-ui.service radio-renew-crl.timer
sudo systemctl is-active ssh nftables openvpn@server.service openvpn-ui.service radio-renew-crl.timer
```

Ne poursuivre qu'après réussite de chaque étape ; ne pas appliquer la substitution si
SHA-256 ou gzip échouent. Refaire les vérifications du [guide principal](restoration.md).

Le bloc ne demande age et sa clé que pour un secours chiffré, selon le
[guide séparé](encryption.md). Son SHA-256 porte sur le `.age`, pas sur le tar.gz déchiffré ;
ne pas modifier les empreintes pour contourner cette distinction.

## Après validation

Les secours locaux ne sont pas purgés automatiquement. Contrôler leur place et les retirer
seulement lorsque la restauration et la collecte de nouvelles sauvegardes sont validées.
Les extractions manuelles en clair et copies temporaires de clés sont des secrets : ne pas
les laisser dans un partage. Éviter toute commande de suppression globale ou non vérifiée.
Conserver les archives NAS d'origine jusqu'à la recette complète sur VPS.
