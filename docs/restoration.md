# Reconstruire et restaurer un serveur

[Accueil restauration](../README.md) · [Dépannage](recovery.md) · [Écosystème](https://github.com/SmallTech2/radio-vpn/blob/main/docs/ecosystem.md)

Cette procédure concerne un **nouveau VPS Debian 13 AMD64**, une sauvegarde de
radio-vpn-backup et un compte administrateur Linux avec sudo. En session root,
omettez `sudo`. Les commandes du VPS sont à saisir dans Bash.

La restauration conserve la CA, les certificats clients, les révocations, les IP VPN
fixes et la base OpenVPN UI. Elle remplace aussi le binaire et les ressources UI par
ceux de l’archive. Le compte Linux, son mot de passe, ses clés SSH, les clés d’hôte,
nftables et les réglages IPv6 du nouveau VPS restent en place.

**Dans cette page**

- [1. Préparer le nouveau VPS](#1-préparer-le-nouveau-vps)
- [2. Installer le socle avec radio-vpn](#2-installer-le-socle-avec-radio-vpn)
- [3. Récupérer la sauvegarde depuis le NAS](#3-récupérer-la-sauvegarde-depuis-le-nas)
- [4. Transférer les fichiers et extraire le ZIP éventuel](#4-transférer-les-fichiers-et-extraire-le-zip-éventuel)
- [5. Préparer et contrôler le fichier SHA-256](#5-préparer-et-contrôler-le-fichier-sha-256)
- [6. Installer radio-vpn-restore et contrôler la compatibilité](#6-installer-radio-vpn-restore-et-contrôler-la-compatibilité)
- [7. Restaurer](#7-restaurer)
- [8. Reconnecter les clients et reprendre l’exploitation](#8-reconnecter-les-clients-et-reprendre-lexploitation)

## 1. Préparer le nouveau VPS

Créer un VPS Debian 13 AMD64 chez l’hébergeur et relever son IPv4 publique. Garder
l’accès à sa console de secours. Autoriser le port SSH utilisé et UDP 1194 ; ne pas
ouvrir TCP 8080 sur Internet. Réunir :

- la clé publique ED25519 du poste administrateur ; la clé privée reste sur ce poste ;
- une sauvegarde et ses empreintes, accessibles sans le VPN à reconstruire ;
- le **réseau VPN de la sauvegarde**, à reprendre à l’identique sur le nouveau serveur ;
- les identifiants de l’interface Web sauvegardée et, si nécessaire, la clé privée age.

Pour une bascule planifiée, arrêter les modifications du serveur source après sa
dernière sauvegarde. Ne pas maintenir deux copies actives de la même PKI qui pourraient
diverger. Les archives non chiffrées contiennent notamment la clé privée de la CA :
conserver les fichiers sur des postes et stockages privés.

## 2. Installer le socle avec radio-vpn

Suivre le [guide d’installation radio-vpn](https://github.com/SmallTech2/radio-vpn/blob/main/docs/installation.md),
y compris la relance manuelle après la préparation Debian et le redémarrage.
Choisir **le même réseau VPN** que la sauvegarde, pour conserver le pare-feu de destination.
L’IP publique et le nom du compte Linux peuvent être différents.

Laisser l’installation se terminer et établir la nouvelle connexion SSH par clé demandée.
Garder cette session ouverte pour la suite. La PKI créée sur ce serveur est provisoire :
ne pas y créer ni distribuer de nouveaux clients avant la restauration. L’installateur
ne doit pas être relancé sur les données restaurées.

**Nouveau VPS — compte administrateur créé par radio-vpn :**

```bash
sudo systemctl is-active ssh nftables openvpn@server.service openvpn-ui.service
mkdir -p "$HOME/sauvegardes-radio"
chmod 700 "$HOME/sauvegardes-radio"
printf 'Répertoire SFTP de destination : %s\n' "$HOME/sauvegardes-radio"
```

Les services doivent être actifs. Le chemin affiché est le véritable dossier de réception
à utiliser ; conserver la connexion SSH ouverte.

## 3. Récupérer la sauvegarde depuis le NAS

**Poste d’administration — navigateur DSM :**

- **ABB** : ouvrir la tâche du serveur et le point souhaité dans le navigateur de
  restauration/ABB Portal. Télécharger le dossier daté contenant `backup.tar.gz`
  (ou `backup.tar.gz.age`) et `SHA256SUMS` ; voir [la récupération dans ABB](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/abb.md#6-contrôler-la-collecte-et-récupérer-les-fichiers).
- **Collecteur personnalisé** : dans File Station, ouvrir le dossier de collecte choisi
  lors de son installation. Télécharger l’archive datée et son fichier de même nom
  terminé par `.sha256`. La [récupération avec le collecteur](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/installation.md#récupérer-manuellement-une-archive)
  explique où retrouver ce dossier.

Garder les noms d’origine. Ne pas demander à ABB de réécrire le VPS source. Si le
téléchargement produit un ZIP, il contient les fichiers à récupérer, pas l’archive
à donner directement à `restore.sh`.

## 4. Transférer les fichiers et extraire le ZIP éventuel

**Poste d’administration — client SFTP :** se connecter au **nouveau VPS**, avec son
IPv4 publique, son port SSH, le compte administrateur créé à l’étape 2 et sa clé privée
SSH du poste. Employer le dossier distant affiché à l’étape 2. Le compte de collecte
`radio-vpn-backup` ne fournit pas de SFTP et ne doit pas être utilisé pour ce transfert.

Transférer le dossier daté ou les fichiers archive + empreintes. Un ZIP peut être extrait
sur le poste avant transfert, avec l’outil d’extraction du système. S’il est déjà sur le
VPS, l’extraire dans un dossier privé séparé :

**Nouveau VPS — même administrateur, uniquement pour un ZIP :**

```bash
sudo apt update
sudo apt install -y unzip
read -r -p 'Chemin absolu du ZIP transféré : ' ZIP
EXTRACT=$(mktemp -d "$HOME/sauvegardes-radio/extrait.XXXXXXXX")
unzip "$ZIP" -d "$EXTRACT"
```

**Même VPS — repérer les fichiers, avec ou sans ZIP :**

```bash
find "$HOME/sauvegardes-radio" -type f \
  \( -name '*.tar.gz' -o -name '*.tar.gz.age' -o -name SHA256SUMS -o -name '*.sha256' \) -print
read -r -p 'Chemin absolu de l archive à restaurer, affiché ci-dessus : ' ARCHIVE
```

Choisir le `.tar.gz` ou `.tar.gz.age` du point voulu, pas le ZIP. Garder la variable
`ARCHIVE` dans cette session pour les commandes suivantes.

## 5. Préparer et contrôler le fichier SHA-256

**Nouveau VPS — même compte et même session :**

```bash
cd "$(dirname "$ARCHIVE")"
if [[ -f SHA256SUMS ]]; then
  cp -- SHA256SUMS "$ARCHIVE.sha256"
fi
chmod 600 "$ARCHIVE" "$ARCHIVE.sha256"
sha256sum -c "$(basename "$ARCHIVE").sha256"
```

Avec ABB, cela copie `SHA256SUMS` sous le nom `backup.tar.gz.sha256` (ou
`backup.tar.gz.age.sha256`). Le collecteur personnalisé fournit déjà le fichier `.sha256`
correspondant. Les noms déclarés dans les empreintes doivent rester ceux des archives.
**Ne poursuivre qu’après `OK`.**

Ce fichier sert à la commande `sha256sum` : le script ne le lit pas automatiquement.
Il vérifie ensuite le manifeste et les empreintes internes de l’archive. SHA-256 ne
prouve pas l’identité de l’auteur ; conserver une origine de sauvegarde fiable.

Pour une archive standard :

```bash
gzip -t "$ARCHIVE"
```

Pour une `.tar.gz.age`, préparer la clé et age selon le [guide dédié](encryption.md),
puis reprendre ci-dessous. Ne pas appliquer gzip au fichier chiffré.

## 6. Installer radio-vpn-restore et contrôler la compatibilité

**Nouveau VPS — même administrateur et même session Bash :**

```bash
sudo apt update
sudo apt install -y git
cd "$HOME"
git clone https://github.com/SmallTech2/radio-vpn-restore.git
cd "$HOME/radio-vpn-restore"
git rev-parse HEAD
sudo bash restore.sh --check "$ARCHIVE"
```

Si le clone existe déjà, utiliser son dossier propre et `git pull --ff-only` au lieu de
le cloner de nouveau. Noter le commit utilisé. Python, OpenSSL, nftables, curl et flock
proviennent du socle installé ; logrotate est requis si une configuration de rotation
est présente sur la source ou la destination. Age n’est requis que pour une archive chiffrée.

Le contrôle demande l’IPv4 publique de destination et le compte administrateur **existant**.
Pour age, il demande également le chemin de la clé privée. Il travaille sur une copie
privée dans `/tmp`, sans arrêter de service ni remplacer de configuration.
Attendre **« Controle de compatibilite reussi »**. En cas d’erreur, suivre le
[dépannage](recovery.md), sans modifier artificiellement la PKI ou les métadonnées.

## 7. Restaurer

**Nouveau VPS — même compte, dans le clone radio-vpn-restore :**

```bash
sudo bash restore.sh
```

1. Donner le chemin de l’archive indiqué par `ARCHIVE` à l’étape 4.
2. Pour age seulement, donner le chemin de la clé privée de déchiffrement.
3. Confirmer l’IPv4 publique du nouveau VPS et le compte Linux existant.
4. Lire le récapitulatif et taper **`RESTAURER`**.

Les contrôles sont répétés avant le remplacement. Le VPN de destination est arrêté
pendant l’opération. Le script crée un secours local de son état précédent, remplace
les données, renouvelle la CRL et redémarre OpenVPN et l’UI. Il ne recrée ni la CA ni
les certificats clients. Les IP VPN fixes et l’historique de révocation sont conservés.
Les configurations de logs absentes de la sauvegarde laissent celles de destination en place.

## 8. Reconnecter les clients et reprendre l’exploitation

Si l’IP publique est identique, utiliser les profils clients existants. Si elle a changé,
modifier uniquement `remote ANCIENNE_IP PORT` en `remote NOUVELLE_IP PORT` dans les copies
déjà distribuées, en conservant le protocole, les clés et certificats. Le script adapte
les profils stockés sur le serveur, pas ceux déjà installés sur les postes clients.

**Nouveau VPS — administrateur :**

```bash
sudo systemctl is-active ssh nftables openvpn@server.service openvpn-ui.service radio-renew-crl.timer
ip -j -4 address show dev tun0
```

Ouvrir une nouvelle connexion SSH avant de fermer la session conservée. Reconnecter un
ancien client avec son profil, puis accéder à l’UI par le VPN ou par le
[tunnel SSH](https://github.com/SmallTech2/radio-vpn/blob/main/docs/security.md#accès-à-openvpn-ui-par-tunnel-ssh).
Les identifiants Web sont ceux de la base sauvegardée. Le serveur VPN garde la première
adresse utilisable du réseau ; les clients retrouvent leurs adresses CCD.

Réinstaller [radio-vpn-backup sur le nouveau VPS](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/vps-installation.md),
puis vérifier la collecte [ABB](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/abb.md#5-configurer-abb)
ou [personnalisée](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/installation.md). Leur compte SSH et le cron ne sont pas recréés par la restauration.
Vérifier sa nouvelle empreinte d’hôte avant de reconfigurer la connexion NAS. Conserver
les sauvegardes d’origine et le secours local pendant la remise en service.

Les commandes de diagnostic, le secours manuel et le traitement d’une interruption
sont dans [Dépannage et secours](recovery.md).
