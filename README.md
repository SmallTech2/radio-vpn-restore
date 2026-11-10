# radio-vpn-restore

Restauration interactive d'une sauvegarde produite par
[radio-vpn-backup](https://github.com/SmallTech2/radio-vpn-backup), sur un VPS
**Debian 13 AMD64 deja prepare avec radio-vpn radio-v2.4**.

Cet outil ne reimplemente pas l'installation. Il restaure la PKI et les clients sans
regenerer leur CA, leurs cles ou certificats. La CRL est renouvelee a partir de l'index
restaure pour remettre a jour sa validite, sans effacer les revocations.
Code a valider sur VPS de test ; aucune Release n'est publiee.

## 1. Preparer le nouveau VPS

Suivre la [procedure radio-vpn](https://github.com/SmallTech2/radio-vpn/blob/radio-v2.4/docs/installation.md)
avec le tag fige **radio-v2.4**, y compris la relance manuelle apres redemarrage.
Choisir le compte Linux du nouveau VPS, fournir sa cle publique et verifier son acces SSH.
L'installation cree une PKI provisoire qui sera remplacee : ne pas creer/distribuer de clients
sur cette installation provisoire. Garder le meme reseau VPN lorsque possible ; le reseau
de la sauvegarde est ensuite conserve et les conflits avec les routes du nouveau VPS sont refuses.

```bash
sudo apt update
sudo apt install -y curl
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://raw.githubusercontent.com/SmallTech2/radio-vpn/radio-v2.4/Radio/deploy-vps.sh \
  -o deploy-vps.sh
sudo bash deploy-vps.sh
```

Le script radio-vpn refuse une installation deja presente : **ne pas le relancer apres
restauration** et ne jamais utiliser `-initialize-only` ou `init-pki` pour restaurer.

Recuperer ce depot, noter le commit (`git rev-parse HEAD`) et conserver cette copie.
Il n'existe pas encore de Release stable des outils de restauration.
Installer le seul prerequis supplementaire :

```bash
sudo apt install -y age
```

Copier sur le nouveau VPS l'archive chiffree et, temporairement, la cle privee age de secours.
Utiliser un repertoire prive 0700, des fichiers 0600, et des droits root pour l'execution.
La cle ne doit pas etre fournie comme texte dans une commande, dans GitHub ou dans un journal.
Si le fichier SHA-256 est disponible, verifier aussi le transfert avec `sha256sum -c`.
Le dechiffrement authentifie de toute facon le contenu chiffre.

## 2. Lancer la restauration

Depuis ce depot, dans une session SSH interactive conservee ouverte :

```bash
sudo bash restore.sh
```

Le script demande uniquement :

1. Chemin local de l'archive `.tar.gz.age`.
2. Chemin de la cle privee age (necessaire au dechiffrement).
3. Nouvelle IPv4 publique, avec detection et confirmation lorsque possible.
4. Compte administrateur **existant**, propose depuis `SUDO_USER` ou l'unique membre du groupe sudo.
5. Confirmation explicite `RESTAURER` apres les controles.

Un utilisateur different de celui du VPS source est accepte. Il doit deja avoir ete cree
et verifie par radio-vpn sur la destination. Ses mots de passe et cles SSH restent ceux
du nouveau VPS. Les services de la reference tournent root et ne contiennent pas de
dependance au nom du compte Linux source ; le nom choisi est inscrit dans les metadonnees
de restauration, sans import d'UID, de `/etc/passwd` ou de `/etc/shadow`.

Avant toute substitution, le script dechiffre dans un dossier root 0700, controle le format,
les empreintes internes, les chemins, les types, permissions et liens, la version de reference,
la PKI, les revocations, les IP fixes et SQLite. Il refuse un reseau VPN incompatible avec
les routes du nouveau VPS. La duree depend surtout de la preparation Debian et de la taille
des donnees ; aucune duree de restauration sur VPS n'est garantie sans recette reelle.

## 3. Remise en service

Apres confirmation : arret de l'UI et du VPN, attente du renouvellement CRL eventuel,
copie de l'etat precedent puis sauvegarde de secours **chiffree** sous
`/var/lib/radio-vpn-restore/before-DATE-ALEA.tar.gz.age`, acces root 0600.
La cle de secours est celle fournie pour le dechiffrement, au format age natif.
Les copies de travail en clair restent dans un dossier root 0700 et sont nettoyees sur
sortie normale ou erreur interceptable. Un SIGKILL/panne peut laisser ce dossier prive :
le traiter comme un secret et le nettoyer apres diagnostic.

L'outil remplace les donnees et ressources UI/PKI, scripts et unites du projet, restaure
les permissions et liens, adapte `RadioPublicIP`, l'adresse serveur dans SQLite,
le modele client et les profils `.ovpn` stockes sur le serveur. Il conserve les hashes
des comptes UI : **la connexion Web reprend avec les identifiants du serveur sauvegarde**.

Les configurations SSH, cles d'hote, acces administrateur, nftables, sysctl et reseau OS
du nouveau VPS sont conserves. Leurs anciennes configurations restent dans l'archive
comme references. Il ne recharge ni ne redemarre SSH et ne remplace pas le pare-feu.
L'installation radio-vpn prealable est responsable de leur preparation securisee.
Les personnalisations hors reference ne sont pas restaurees automatiquement.

Les services VPN/UI et timers CRL/logrotate sont actives, journald recharge par redemarrage,
puis controles : certificats/cles/CRL, SQLite, configuration serveur attendue, etat systemd,
adresse CIDR de tun0, ecoute UDP 1194 et page de connexion UI sur localhost.
OpenVPN est reellement demarre pour valider le chargement de sa configuration ; une simple
verification de texte ne serait pas une validation fonctionnelle.

**Les sessions VPN du VPS de destination sont interrompues pendant la restauration.**
Si l'IP publique change, adapter `remote` dans les profils deja distribues, sans changer
les certificats. Les profils copies sur les postes ne sont pas modifies a distance.
Reinstaller ensuite radio-vpn-backup avec les cles publiques de collecte et de chiffrement
pour reprendre les sauvegardes automatiques. Adapter l'adresse du VPS dans la tache NAS et
verifier sa nouvelle empreinte SSH depuis une console de confiance avant de mettre a jour
`known_hosts` ; ne pas importer les cles SSH d'hote de l'ancien serveur.
Pour une bascule planifiee, faire une derniere sauvegarde apres gel de l'administration
du serveur source et le maintenir hors service apres bascule pour eviter des index divergents.

## 4. Echec et retour arriere

En cas d'echec apres remplacement, le script tente d'arreter VPN/UI/CRL, de remettre les
donnees precedentes et de retablir les services qui etaient actifs. SSH et nftables restent
ceux de la destination. Tout echec du retour arriere est affiche explicitement.
Une panne ou un SIGKILL ne peut pas etre intercepte : utiliser alors la console/SSH conserve.

La sauvegarde `before-...tar.gz.age` est un **secours local** de l'installation remplacee,
pas une archive de collecte au format v1. Pour une recuperation manuelle en maintenance :

```bash
sudo -i
umask 077
mkdir -m 700 /root/radio-vpn-secours
age -d -i /chemin/cle-age-privee -o /root/radio-vpn-secours.tar.gz \
  /var/lib/radio-vpn-restore/before-DATE-ALEA.tar.gz.age
gzip -t /root/radio-vpn-secours.tar.gz
tar -xpf /root/radio-vpn-secours.tar.gz --same-owner -C /root/radio-vpn-secours
systemctl stop openvpn-ui.service openvpn@server.service radio-renew-crl.timer
# Depuis le repertoire du depot, remplace uniquement les chemins fixes de l'outil :
python3 scripts/restore_data.py replace /root/radio-vpn-secours /
systemctl daemon-reload
systemctl start openvpn@server.service openvpn-ui.service radio-renew-crl.timer
```

Ne lancer cette procedure que sur le secours genere par cet outil et avec un operateur
present. Verifier les services avant d'effacer les copies en clair. Conserver la cle
originale hors VPS ; supprimer sa copie temporaire du serveur apres la recette. Les secours
chiffres locaux ne sont pas purges automatiquement : les retirer apres validation pour
ne pas remplir le disque a force de restaurations.

## 5. Recette et limites

Realiser le [plan de recette](docs/validation.md) : ancien certificat et IP fixe conserves,
certificat revoque refuse, nouveau client cree, SSH/UI/pare-feu et redemarrage verifies.
Verifier aussi une restauration avec nouveau compte Linux et nouvelle IP publique.

Les tests automatiques couvrent des PKI jetables, SQLite, les archives dangereuses,
la preservation des secrets/certificats et les substitutions de fichiers en repertoires
temporaires. Ils ne prouvent pas le fonctionnement de systemd, SSH, tun0 ou d'un hebergeur.
Un serveur ou une CA dont les certificats sont expires, des schemas UI differents, des
chemins personnalises ou une autre version de radio-vpn sont refuses/non pris en charge.
Les clients avec cle privee chiffree conservent leur mot de passe ; l'outil ne le connait pas.

La sauvegarde ne peut contenir les modifications posterieures a sa creation : une ancienne
archive peut perdre des clients ou des revocations recentes. Le chiffrement ne prouve pas
que le VPS source etait sain. Conserver plusieurs generations et choisir un point fiable.

## Licence et tests

[MIT](LICENSE). Outil compagnon de Radio Bonheur pour radio-vpn, derive de
[d3vilh/openvpn-ui](https://github.com/d3vilh/openvpn-ui) ; attributions conservees.
Tests : `python3 -B -m unittest discover -s tests -v`.
