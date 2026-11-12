# Radio VPN Restore

[Installation](#installation) · [Guides utilisateur](#guides-utilisateur) · [Écosystème Radio VPN](#écosystème-radio-vpn)

## Présentation

radio-vpn-restore remet en service les données d’une archive de [radio-vpn-backup](https://github.com/SmallTech2/radio-vpn-backup)
sur un VPS **Debian 13 AMD64 préalablement reconstruit avec radio-vpn**. Il conserve la CA,
les certificats clients, les révocations, les IP VPN fixes et la base OpenVPN UI : les
équipements peuvent reprendre leur connexion sans renouveler leurs certificats.
Si l’IP publique change, leurs profils doivent être adaptés.

Le parcours interactif contrôle l’archive et la compatibilité avant remplacement ;
le mode `--check` permet cette vérification sans arrêter les services. La restauration
préserve les accès SSH et les réglages réseau propres au nouveau VPS, puis remet en route
OpenVPN et l’UI. La destination doit utiliser **le même réseau VPN** que la sauvegarde.

Une sauvegarde d’un autre outil ou une destination préparée autrement n’est pas garantie
compatible ; voir le [périmètre de l’écosystème](https://github.com/SmallTech2/radio-vpn/blob/main/docs/ecosystem.md#périmètre-de-compatibilité).
La compatibilité dépend du format et des composants, pas d’une égalité de versions.
Les versions et commits d’origine sont conservés.

Solution validée le 12 novembre 2026 sur Debian 13.7.

**Version officielle actuelle : [v1.0.0](https://github.com/SmallTech2/radio-vpn-restore/releases/tag/v1.0.0).**
Référence : [VERSION](VERSION). Les trois projets partagent ce même numéro de version ;
la distribution officielle associe radio-vpn, radio-vpn-backup et radio-vpn-restore en `v1.0.0`.

## Installation

**[Ouvrir la procédure complète de reconstruction et restauration](docs/restoration.md).**

Elle détaille la préparation du nouveau VPS avec radio-vpn, la récupération depuis le NAS,
le transfert, le contrôle SHA-256, le clonage de radio-vpn-restore, le contrôle préalable
`--check` et la restauration. Commencer au début sur un VPS vierge ; si le socle est déjà
prêt, rejoindre [l’installation de l’outil et le contrôle de compatibilité](docs/restoration.md#6-installer-radio-vpn-restore-et-contrôler-la-compatibilité).

## Guides utilisateur

- [Reconstruire le serveur](docs/restoration.md#1-préparer-le-nouveau-vps) : prérequis et installation du socle.
- [Récupérer et transférer une archive](docs/restoration.md#3-récupérer-la-sauvegarde-depuis-le-nas) : ABB ou collecteur personnalisé.
- [Contrôler la compatibilité](docs/restoration.md#6-installer-radio-vpn-restore-et-contrôler-la-compatibilité) : `--check` sans arrêter de service ni remplacer de configuration.
- [Restaurer les données](docs/restoration.md#7-restaurer) : confirmation et remplacement ; le VPN de destination est interrompu pendant l’opération.
- [Reconnecter les clients](docs/restoration.md#8-reconnecter-les-clients-et-reprendre-lexploitation) : contrôles et adaptation de `remote` si l’IPv4 publique change.

## Sauvegarde et restauration

- [Installer radio-vpn-backup et produire une archive](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/vps-installation.md).
- Collecter avec [Synology ABB](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/abb.md) ou le [collecteur personnalisé](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/installation.md).
- [Suivre la restauration complète](docs/restoration.md).
- [Réinstaller ensuite la sauvegarde et vérifier la collecte](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/vps-installation.md) : le compte de collecte et son cron ne sont pas recréés par la restauration.

## Sécurité et maintenance

Le compte Linux, son mot de passe, ses clés SSH, les clés d’hôte, nftables et les réglages
IPv6 de destination sont conservés. L’UI et ses identifiants sont ceux de la base restaurée.
Les archives non chiffrées contiennent la clé privée de la CA : les conserver dans un
emplacement protégé. Une `.tar.gz` ne demande ni age ni clé de déchiffrement.

- [Archive chiffrée avec age](docs/encryption.md) : clé privée requise uniquement pour ce format.
- [Dépannage et secours](docs/recovery.md) : contrôles avant remplacement et retour arrière.
- [Contrôles après remise en service](docs/restoration.md#8-reconnecter-les-clients-et-reprendre-lexploitation).
- [Maintenance du serveur VPN](https://github.com/SmallTech2/radio-vpn/blob/main/docs/maintenance.md).

## Références techniques

- [Script de restauration](restore.sh) : parcours interactif et contrôle préalable.
- [Lecture et intégrité des archives](scripts/archive.py).
- [Validation et remplacement des données](scripts/restore_data.py).
- [Format de sauvegarde et compatibilité](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/format.md).
- [Suivi technique](docs/validation.md).

### Licence et crédits

[MIT](LICENSE). Outil compagnon de Radio Bonheur pour radio-vpn, dérivé de
[d3vilh/openvpn-ui](https://github.com/d3vilh/openvpn-ui), avec les attributions conservées.

## Écosystème Radio VPN

- [radio-vpn](https://github.com/SmallTech2/radio-vpn) : [installer un serveur VPN](https://github.com/SmallTech2/radio-vpn/blob/main/docs/installation.md).
- [radio-vpn-backup](https://github.com/SmallTech2/radio-vpn-backup) : [sauvegarder ce serveur](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/vps-installation.md).
- [radio-vpn-restore](https://github.com/SmallTech2/radio-vpn-restore) : [reconstruire et restaurer](docs/restoration.md).

La [présentation de l’écosystème](https://github.com/SmallTech2/radio-vpn/blob/main/docs/ecosystem.md)
explique les rôles et dépendances des trois projets.
