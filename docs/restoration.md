# Restaurer sur un nouveau VPS Debian 13

Mode standard : archive `.tar.gz`, **sans age ni clé de déchiffrement**.
La restauration remplace la PKI provisoire du nouveau serveur par celle de la sauvegarde,
avec ses certificats, révocations, IP fixes, base et identifiants Web.

Chaque bloc précise la machine et le compte. Les commandes VPS utilisent Bash. Les
chemins de travail sont créés sous le vrai dossier personnel, pas sous un volume supposé.
Ne pas exécuter simultanément cette procédure et une administration du serveur source.

## 1. Avant de commencer

Prévoir :

- Un VPS Debian 13 vierge **AMD64**, une IPv4 publique et l'accès SSH/console de l'hébergeur.
- Votre poste d'administration et sa clé privée SSH ; la clé **publique** correspondante
  sera fournie à radio-vpn pour le compte Linux du nouveau VPS.
- Une archive récente du NAS et son fichier `.sha256`, accessibles indépendamment du VPN.
- Les informations du serveur sauvegardé : réseau VPN, compte UI et point de sauvegarde choisi.
- Du temps pour vérifier une nouvelle connexion SSH et un client VPN après remise en service.

Les archives non chiffrées contiennent la clé privée de la CA et les clés clients. Ce choix
est volontaire et son risque accepté : stockage privé, fichiers 0600, dossiers 0700, pas
de publication ou de partage public. Une ancienne archive perd les créations et révocations
postérieures ; choisir un point fiable. SHA-256 ne prouve pas l'identité de son auteur.

Pour une bascule planifiée : arrêter l'administration du VPS source, réaliser une dernière
sauvegarde puis sa collecte, et ne plus modifier sa PKI. Après bascule, maintenir l'ancien
serveur hors service : deux copies actives pourraient faire diverger index et numéros de série.

## 2. Préparer complètement le nouveau VPS avec radio-vpn

**Poste d'administration :** créer le VPS chez l'hébergeur, relever l'IPv4 publique et ouvrir
la première connexion SSH fournie par l'hébergeur, en IPv4. Autoriser dans son pare-feu le
port SSH réellement utilisé et UDP 1194. Ne pas ouvrir TCP 8080 sur Internet.

**Nouveau VPS — premier compte root ou administrateur fourni par l'hébergeur :**

```bash
sudo apt update
sudo apt install -y curl git
cd "$HOME"
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/SmallTech2/radio-vpn/radio-v2.4/Radio/deploy-vps.sh \
  -o deploy-vps.sh
sudo bash "$HOME/deploy-vps.sh"
```

En session root, omettre `sudo` dans les commandes de ce guide. Le tag figé `radio-v2.4`
est un exemple reproductible pour préparer la destination, pas une obligation de
version pour la sauvegarde. Ne pas remplacer cette URL par `main`. La compatibilité
repose sur les composants présents, y compris pour une source radio-v2.1.

Le premier passage met Debian à niveau et demande confirmation avant redémarrage.
**Attendre le redémarrage, rouvrir une session avec le même compte initial**, puis :

```bash
sudo bash "$HOME/deploy-vps.sh"
```

Le script ne reprend pas automatiquement. Ne pas télécharger une nouvelle copie entre
ces deux passages. Il demande l'IPv4 publique, le réseau VPN, le compte Linux à créer,
sa clé publique ED25519, l'identité PKI et les mots de passe. Choisir impérativement le
même réseau VPN que la sauvegarde : le pare-feu et les réglages réseau du nouveau VPS
sont conservés. Un réseau différent ou un conflit de routes bloque le contrôle préalable.

La CA créée ici est **provisoire** : ne pas créer/distribuer de clients sur cette installation.
Le mot de passe Linux choisi reste celui de la console de secours. Le compte UI et son
mot de passe seront ensuite ceux de la base restaurée, pas ceux choisis provisoirement.

Quand radio-vpn le demande, ouvrir une **deuxième connexion SSH**, avec le nouveau compte
et sa clé privée sur le poste administrateur. Suivre la commande affichée par l'installateur
et garder les deux sessions ouvertes ; sa preuve de connexion par clé est contrôlée avant
durcissement. Attendre le bilan de fin d'installation, sans erreur.

L'installateur refuse une installation/PKI existante. Ne pas le relancer pour restaurer.
Ne jamais appeler `init-pki`, `init_all` ou `-initialize-only` sur les données restaurées.

**Nouveau VPS — nouveau compte administrateur choisi, avec sudo :**

```bash
sudo cat /etc/radio-vpn-deployed
sudo systemctl is-active ssh nftables openvpn@server.service openvpn-ui.service
mkdir -p "$HOME/sauvegardes-radio"
chmod 700 "$HOME/sauvegardes-radio"
printf 'Dossier de réception réel : %s\n' "$HOME/sauvegardes-radio"
```

Les services doivent être actifs et les composants radio-vpn complets ; le numéro de
version seul ne détermine pas la compatibilité. Ne poursuivre qu'après une
installation complète ; une configuration partielle ne constitue pas le prérequis attendu.

## 3. Récupérer une archive du NAS

### Avec Active Backup for Business

**NAS — opérateur ABB :** ouvrir la tâche du VPS et le point voulu dans le navigateur
ABB de restauration. Télécharger le dossier daté contenant `backup.tar.gz` et `SHA256SUMS`.
Ne pas restaurer ces fichiers vers le VPS source. Le compte DSM et le stockage sont ceux
de la tâche ABB ; ils ne sont pas nécessairement ceux du collecteur personnalisé.

**Poste d’administration — Bash, dans le dossier téléchargé :**

```bash
sha256sum -c SHA256SUMS
cp SHA256SUMS backup.tar.gz.sha256
```

Sous Windows sans Bash, faire une copie de `SHA256SUMS` nommée `backup.tar.gz.sha256`
dans l’Explorateur. Ce sont les mêmes empreintes ; le contrôle sera fait sur le nouveau VPS.
Conserver le nom `backup.tar.gz` et transférer les deux fichiers selon les blocs ci-dessous.
Le contenu de l’archive peut provenir de radio-v2.1 ; sa version originale reste conservée.

### Avec le collecteur personnalisé

**Poste d'administration — navigateur DSM, compte NAS `vpnbackup` :**

1. Dans File Station, ouvrir `home/radio-vpn/archives/vps1`, créé par le guide de sauvegarde.
   Si vous avez choisi un autre identifiant VPS, ouvrir son sous-dossier.
2. Choisir le point récent correspondant au bon serveur. Le nom contient sa date UTC :
   `AAAAMMJJTHHMMSSZ-xxxxxxxx.tar.gz`. Vérifier le journal de collecte si nécessaire.
3. Télécharger **séparément** cette archive et le fichier de même nom suivi de `.sha256`
   pour éviter qu'un téléchargement groupé les enferme dans un ZIP.
4. Les conserver dans un dossier privé de votre poste. Afficher les extensions des fichiers
   dans l'explorateur pour identifier les deux noms exacts. Ne pas les ouvrir avec un éditeur.

Le compte VPS `radio-vpn-backup` ne possède pas de SFTP ou de shell libre : il n'est pas
utilisé pour le transfert vers le nouveau serveur. Employer le compte administrateur du
**nouveau VPS**, avec la clé SSH validée à l'étape précédente.

### Transfert depuis Windows

**Poste d'administration — PowerShell**, dans une fenêtre distincte des sessions SSH :

```powershell
$Archive = (Read-Host 'Chemin complet de l archive téléchargée').Trim('"')
$Cle = (Read-Host 'Chemin complet de votre clé privée SSH administrateur du nouveau VPS').Trim('"')
$Compte = Read-Host 'Compte Linux administrateur du nouveau VPS'
$Ip = Read-Host 'IPv4 publique du nouveau VPS'
$Port = Read-Host 'Port SSH du nouveau VPS [22]'
if (-not $Port) { $Port = '22' }
Get-Item -LiteralPath $Archive, ($Archive + '.sha256'), $Cle
scp -P $Port -i $Cle $Archive ($Archive + '.sha256') "${Compte}@${Ip}:sauvegardes-radio/"
```

Pour obtenir un chemin Windows, utiliser **Copier en tant que chemin d'accès** dans
l'explorateur ; `Trim` retire les guillemets ajoutés. Vérifier les fichiers affichés avant
le transfert ; s'il manque le `.sha256`, le télécharger avec son nom inchangé.
`-P` indique le port pour `scp`, `-i` votre clé SSH, pas la clé de collecte NAS.
Le répertoire de destination est celui créé sous le dossier personnel du nouveau compte.
Une éventuelle phrase secrète de votre clé est demandée localement, jamais copiée au VPS.

### Alternative Linux/macOS

**Poste d'administration — Bash**, à la place du bloc PowerShell :

```bash
read -r -p 'Chemin complet de l archive locale : ' ARCHIVE_LOCAL
read -r -p 'Chemin complet de la clé privée SSH administrateur : ' SSH_PRIVATE
read -r -p 'Compte Linux du nouveau VPS : ' VPS_ADMIN
read -r -p 'IPv4 publique du nouveau VPS : ' VPS_IP
read -r -p 'Port SSH [22] : ' VPS_PORT
VPS_PORT=${VPS_PORT:-22}
scp -P "$VPS_PORT" -i "$SSH_PRIVATE" "$ARCHIVE_LOCAL" "$ARCHIVE_LOCAL.sha256" \
  "$VPS_ADMIN@$VPS_IP:sauvegardes-radio/"
```

## 4. Vérifier le transfert et installer l'outil de restauration

**Nouveau VPS — compte administrateur choisi, session SSH conservée :**

```bash
cd "$HOME/sauvegardes-radio"
ls -l
read -r -p 'Nom exact du fichier .tar.gz affiché ci-dessus : ' ARCHIVE_NAME
ARCHIVE="$PWD/$ARCHIVE_NAME"
chmod 600 "$ARCHIVE" "$ARCHIVE.sha256"
sha256sum -c "$ARCHIVE_NAME.sha256"
gzip -t "$ARCHIVE"
```

Ne poursuivre qu'après `OK` et la réussite silencieuse de gzip. Le nom demandé est celui
affiché par `ls`, pas un exemple à recopier. Le chemin absolu `ARCHIVE` est maintenant connu.
Pour une archive `.age`, suivre le [guide séparé](encryption.md) ; ne pas lui appliquer gzip.

**Nouveau VPS — même compte :**

```bash
sudo apt update
sudo apt install -y git
cd "$HOME"
git clone https://github.com/SmallTech2/radio-vpn-restore.git
cd "$HOME/radio-vpn-restore"
git rev-parse HEAD
printf 'Archive à indiquer au script : %s\n' "$ARCHIVE"
sudo bash restore.sh --check "$ARCHIVE"
```

Noter le commit utilisé. Si ce dépôt est déjà présent, vérifier `git status` puis utiliser
`git pull --ff-only` dans son dossier propre, sans le cloner par-dessus. Aucun paquet age
n'est demandé pour une archive standard. Python, OpenSSL, nftables et curl
proviennent de l'installation radio-vpn préalable. Logrotate n'est requis que si une
configuration de rotation est présente dans la sauvegarde ou sur la destination.

Le contrôle `--check` demande l’IPv4 publique et le compte existant, puis s’arrête avec
« Controle de compatibilite reussi » sans remplacement ni arrêt de service. Seule une
copie de travail privée sous `/tmp` est modifiée puis supprimée. Il vérifie les chemins,
la PKI, ses clés et signatures, les révocations, les CCD/IP fixes, SQLite et son schéma,
la configuration UI/OpenVPN, le réseau de destination, les routes, SSH et nftables.

`crlnumber`, les références SSH/nftables/IPv6 et les configurations de logs peuvent être
absents de la sauvegarde. Les fichiers essentiels, dont `index.txt` et `crl.pem`, restent
obligatoires. Les versions et commits d’origine ne sont pas remplacés par ceux du nouveau VPS.

**Uniquement après réussite du contrôle, même compte et même dépôt :**

```bash
sudo bash restore.sh
```

La restauration repose sur les mêmes contrôles et les répète. Elle ne transforme pas
un contrôle statique en garantie de fonctionnement réel : les étapes client/SSH ci-dessous
restent nécessaires. Si l’environnement change entre les deux commandes, refaire le contrôle.

## 5. Répondre à l'assistant

**Nouveau VPS — même session, script exécuté avec sudo :**

1. Donner le chemin absolu de l'archive affiché précédemment.
2. Confirmer/corriger l'IPv4 publique proposée : celle du **nouveau** VPS.
3. Confirmer le compte administrateur existant proposé. Il peut différer de celui du
   serveur sauvegardé, mais doit être un compte sudo avec une clé SSH déjà installée.
4. Lire le récapitulatif, puis taper `RESTAURER` pour autoriser les remplacements.

Le format est reconnu par le contenu. Une `.tar.gz` ne déclenche aucune demande de clé.
Les vérifications gzip, empreintes internes, chemins, permissions, liens, SQLite, PKI,
révocations, IP fixes et routes précèdent la confirmation et le remplacement des données.
Un manque d’espace, un composant manquant, un réseau différent ou un schéma incompatible
peuvent provoquer un refus ; un numéro de version différent ne suffit pas à bloquer.

Les accès SSH, clés d'hôte, mot de passe Linux, pare-feu nftables et réglages réseau du
nouveau VPS sont conservés. Les paramètres SSH/réseau du serveur sauvegardé ne sont pas
recopiés aveuglément. Les données VPN/UI sont remplacées ; le VPN de destination est
interrompu pendant la restauration. La CRL est renouvelée, **pas la CA ni les certificats**.

## 6. Contrôler le résultat immédiatement

**Nouveau VPS — administrateur :**

```bash
sudo systemctl is-active ssh nftables openvpn@server.service openvpn-ui.service radio-renew-crl.timer
if [ -f /etc/logrotate.d/openvpn ]; then sudo systemctl is-active logrotate.timer; fi
sudo journalctl -u openvpn@server.service -u openvpn-ui.service -n 80 --no-pager
ip -j -4 address show dev tun0
sudo ss -lunp
curl --fail --silent --show-error http://127.0.0.1:8080/login >/dev/null
sudo cat /etc/radio-vpn-deployed
sudo /usr/sbin/sshd -t
```

Attendre des services actifs, `tun0` sur la première adresse utilisable du réseau sauvegardé,
UDP 1194 et une page de connexion UI accessible localement. Les contrôles du script ne
remplacent pas une connexion réelle depuis un client. Ouvrir aussi une nouvelle session SSH
avec le compte choisi avant de fermer celles conservées pendant l'intervention.

**Poste d'administration :** accéder à OpenVPN UI par votre tunnel SSH ou par le VPN.
Utiliser les identifiants Web du serveur sauvegardé. Vérifier la liste des clients et IP fixes.
Selon l’interface restaurée, les certificats révoqués peuvent être masqués dans la liste
principale ; l’affichage seul ne prouve pas que leur historique et leur refus fonctionnent.

## 7. Vérifier certificats, IP fixes et révocations

**Nouveau VPS — administrateur**, choisir le nom exact d'un ancien client valide connu :

```bash
read -r -p 'Nom exact d un ancien certificat client valide : ' CLIENT
sudo openssl x509 -in "/usr/share/easy-rsa/pki/issued/$CLIENT.crt" -noout -serial -fingerprint -sha256
sudo cat "/etc/openvpn/staticclients/$CLIENT"
sudo openssl x509 -in /usr/share/easy-rsa/pki/ca.crt -noout -fingerprint -sha256
sudo openssl crl -in /usr/share/easy-rsa/pki/crl.pem -noout -lastupdate -nextupdate
sudo awk -F '\t' '$1=="R" {print "R", $4, $6}' /usr/share/easy-rsa/pki/index.txt
```

Comparer l'empreinte et la série du client, l'empreinte CA et l'IP avec vos valeurs de
référence, relevées avant incident ou dans l'archive. La CRL peut avoir une nouvelle date,
mais les entrées `R` et les identités doivent rester présentes. Ne jamais diffuser les clés privées.

Pour obtenir les valeurs de référence dans une **archive standard**, sans extraire de clé,
**nouveau VPS — même compte**, avec `ARCHIVE` défini à l'étape 4 et `CLIENT` ci-dessus :

```bash
tar -xOf "$ARCHIVE" payload/usr/share/easy-rsa/pki/ca.crt | openssl x509 -noout -fingerprint -sha256
tar -xOf "$ARCHIVE" "payload/usr/share/easy-rsa/pki/issued/$CLIENT.crt" | openssl x509 -noout -serial -fingerprint -sha256
tar -xOf "$ARCHIVE" "payload/etc/openvpn/staticclients/$CLIENT"
```

Ces commandes ne s'appliquent pas directement à un `.age`. Dans ce cas utiliser vos
relevés avant sauvegarde, ou la copie déchiffrée dans un dossier privé sur une machine de test.

**Poste client de test :** si l'IP publique a changé, modifier uniquement la valeur après
`remote` dans une copie du profil `.ovpn` existant, en conservant son port et protocole.
Ne pas remplacer les blocs de certificats ou de clés. La restauration adapte les profils
stockés sur le serveur, pas les copies déjà distribuées.

1. Connecter l'ancien client valide : son certificat initial doit fonctionner et son IP
   VPN doit correspondre à celle du CCD affiché. Vérifier la communication attendue avec un autre client.
2. Essayer un profil de test déjà révoqué : la connexion doit être refusée. Contrôler le
   journal avec `sudo tail -n 80 /var/log/openvpn/openvpn.log` sur le nouveau VPS.
3. Dans l'UI, créer un nouveau client de test avec une IP libre du réseau restauré,
   télécharger son profil et vérifier sa connexion. Cela contrôle la capacité de la CA
   restaurée à signer de nouveaux certificats sans conflit d'historique.

Utiliser des clients/profils de test ; ne pas révoquer un client métier pour cette recette.
Voir la [check-list de validation](validation.md).

## 8. Vérifier après redémarrage et reprendre les sauvegardes

**Nouveau VPS — administrateur**, après réussite des contrôles et accord pour la coupure :

```bash
sudo reboot
```

Le redémarrage coupe les sessions et les connexions VPN. Après reconnexion, refaire les
commandes de l'étape 6, les essais client valide/révoqué et la vérification d'une nouvelle
connexion SSH. Contrôler aussi :

```bash
sudo systemctl is-enabled openvpn@server.service openvpn-ui.service radio-renew-crl.timer
if [ -f /etc/logrotate.d/openvpn ]; then sudo systemctl is-enabled logrotate.timer; fi
systemctl list-timers --all radio-renew-crl.timer logrotate.timer
sudo nft list ruleset
sysctl net.ipv6.conf.all.disable_ipv6 net.ipv6.conf.default.disable_ipv6
```

Les paramètres IPv6 contrôlés sont ceux de la destination. Une sauvegarde sans
configuration IPv6 ou de logs n’ajoute pas ces fonctions à une ancienne installation.

Réinstaller ensuite `radio-vpn-backup` en suivant son
[guide](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/installation.md).
Le compte SSH de collecte et cron ne sont pas recréés par la restauration. Dans la
configuration NAS, mettre la nouvelle adresse/port et vérifier la **nouvelle clé d'hôte**
avant de mettre à jour `known_hosts`. Ne pas importer les clés d'hôte de l'ancien VPS.
Faire une sauvegarde manuelle et une collecte, puis vérifier leur prochain cycle automatique.

Conserver les sauvegardes d'origine jusqu'à validation. Les secours locaux consomment
de l'espace et ne sont pas purgés automatiquement. Voir le [retour arrière](recovery.md).
