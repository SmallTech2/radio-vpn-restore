# radio-vpn-restore

Restaure une archive de **radio-vpn-backup** sur un VPS **Debian 13 AMD64 préalablement
reconstruit avec radio-vpn**, en conservant la CA, les certificats clients, les révocations,
les IP VPN fixes et les données OpenVPN UI. La CRL est renouvelée sans recréer les certificats.

Solution validée le 12 novembre 2026 sur Debian 13.7.

## Choisir votre procédure

| Votre objectif | Projet | Procédure directe |
| --- | --- | --- |
| Installer un serveur VPN | [radio-vpn](https://github.com/SmallTech2/radio-vpn) | [Installer le serveur VPN](https://github.com/SmallTech2/radio-vpn/blob/main/README.md#installer-le-serveur-vpn) |
| Sauvegarder ce serveur | [radio-vpn-backup](https://github.com/SmallTech2/radio-vpn-backup) | [Installer la sauvegarde sur le VPS](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/vps-installation.md) |
| Reconstruire et restaurer | [radio-vpn-restore](https://github.com/SmallTech2/radio-vpn-restore) | [Reconstruire et restaurer le serveur](docs/restoration.md) |

Voir la [présentation générale](https://github.com/SmallTech2/radio-vpn/blob/main/docs/ecosystem.md).
Une sauvegarde d’un autre outil ou une destination préparée autrement n’est pas garantie
compatible. Il s’agit du périmètre commun, pas d’une impossibilité technique absolue.

## Restaurer après perte du VPS

Suivre la [procédure chronologique](docs/restoration.md) : reconstruction, récupération
NAS, transfert SFTP, extraction éventuelle du ZIP, contrôle SHA-256 et installation de l’outil.
La destination doit utiliser le **même réseau VPN** que la sauvegarde.

Une fois le dépôt cloné et l’archive vérifiée, sur le **nouveau VPS, compte administrateur** :

```bash
cd "$HOME/radio-vpn-restore"
read -r -p 'Chemin absolu de l archive locale : ' ARCHIVE
sudo bash restore.sh --check "$ARCHIVE"
```

Après réussite, lancer la restauration interactive :

```bash
sudo bash restore.sh
```

Donner le chemin de l’archive, confirmer l’IP publique et le compte Linux existant, puis
taper `RESTAURER`. Le VPN de destination est interrompu pendant le remplacement.
`--check` ne remplace aucune configuration et n’arrête aucun service.

## Données et accès

Le script ne régénère ni la CA ni les certificats sauvegardés. Le compte Linux, son
mot de passe, ses clés SSH, les clés d’hôte, nftables et les réglages IPv6 de destination
restent en place. L’UI et son mot de passe sont ceux de la base restaurée. Si l’IPv4
publique change, adapter `remote` dans les profils déjà distribués, sans renouveler les certificats.

Le format est détecté automatiquement. Une `.tar.gz` ne demande ni age ni clé ; une
archive chiffrée demande le chemin de sa clé privée age. Les versions et commits d’origine
sont conservés ; la compatibilité dépend des composants et du format, pas d’une version unique.
Les archives non chiffrées contiennent la clé privée de la CA : les conserver en privé.

Après remise en service, [réinstaller radio-vpn-backup](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/vps-installation.md)
et vérifier la collecte NAS : la restauration ne recrée ni le compte de collecte ni son cron.

## Guides

[Restauration](docs/restoration.md) · [Chiffrement age](docs/encryption.md) ·
[Dépannage et secours](docs/recovery.md).

## Licence

[MIT](LICENSE). Outil compagnon de Radio Bonheur pour radio-vpn, dérivé de
[d3vilh/openvpn-ui](https://github.com/d3vilh/openvpn-ui), avec les attributions conservées.
