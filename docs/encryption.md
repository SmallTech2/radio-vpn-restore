# Option : restaurer une archive age

Cette page concerne seulement les `.tar.gz.age`. Pour une `.tar.gz`, suivre directement
la [procédure standard](restoration.md) : aucun outil age ni aucune clé ne sont nécessaires.
L'activation de la sauvegarde chiffrée est expliquée dans le
[guide backup](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/encryption.md).

## 1. Rassembler les fichiers

**Poste d'administration — navigateur DSM, compte NAS `vpnbackup` :** télécharger depuis
`home/radio-vpn/archives/vps1` l'archive `.tar.gz.age` et son fichier `.age.sha256` séparément.
Employer votre véritable identifiant VPS si ce n'est pas `vps1`.

**Poste de confiance :** retrouver la clé privée age créée au moment de l'activation,
dans votre coffre ou votre support hors ligne. Ce n'est ni la clé SSH NAS, ni la clé SSH
administrateur. Ne jamais la recréer en espérant retrouver la même clé ; sa perte empêche
le déchiffrement. Garder l'original hors du VPS et n'en transférer qu'une copie temporaire.

## 2. Transférer puis installer age

Préparer d'abord le nouveau VPS et son dossier privé `sauvegardes-radio` comme dans le
guide standard. Transférer l'archive et son SHA-256 avec le même bloc PowerShell/Bash,
en choisissant le fichier `.tar.gz.age`. Ne pas appliquer `gzip -t` au fichier chiffré.

**Poste Windows — PowerShell**, dans la session ayant conservé `$Port`, `$Cle`, `$Compte`
et `$Ip` du guide standard, transférer la copie temporaire de la clé privée age :

```powershell
$AgeKey = (Read-Host 'Chemin complet de la copie de clé privée age').Trim('"')
Get-Item -LiteralPath $AgeKey
scp -P $Port -i $Cle $AgeKey "${Compte}@${Ip}:sauvegardes-radio/"
```

**Poste Linux/macOS — Bash**, alternative avec les variables du transfert standard :

```bash
read -r -p 'Chemin complet de la copie de clé privée age : ' AGE_KEY_LOCAL
scp -P "$VPS_PORT" -i "$SSH_PRIVATE" "$AGE_KEY_LOCAL" "$VPS_ADMIN@$VPS_IP:sauvegardes-radio/"
```

**Nouveau VPS — compte administrateur Linux :**

```bash
sudo apt update
sudo apt install -y age
cd "$HOME/sauvegardes-radio"
ls -l
read -r -p 'Nom exact de l archive .tar.gz.age affichée : ' ARCHIVE_NAME
read -r -p 'Nom exact du fichier de clé age affiché : ' AGE_KEY_NAME
ARCHIVE="$PWD/$ARCHIVE_NAME"
AGE_KEY="$PWD/$AGE_KEY_NAME"
chmod 600 "$ARCHIVE" "$ARCHIVE.sha256" "$AGE_KEY"
sha256sum -c "$ARCHIVE_NAME.sha256"
printf 'Archive : %s\nClé temporaire : %s\n' "$ARCHIVE" "$AGE_KEY"
cd "$HOME/radio-vpn-restore"
sudo bash restore.sh
```

Installer le dépôt comme dans le guide standard s'il n'est pas encore présent. Les deux
noms saisis sont ceux de `ls`, pas des chemins d'exemple. Vérifier `OK` avant de continuer.

## 3. Répondre au script et terminer

**Nouveau VPS — même session :** `sudo bash restore.sh --check "$ARCHIVE"` permet
d’abord de vérifier sans remplacement. Après réussite, `sudo bash restore.sh` lance la
restauration. Les deux modes utilisent la même détection et le même déchiffrement.
Donner le chemin complet de l’archive si demandé. Le script reconnaît
son contenu et demande alors le chemin de la clé privée age, affiché ci-dessus. Il n'affiche
pas cette clé et ne demande son chemin qu’une fois par exécution. La même clé est
réutilisée pour chiffrer le secours lors de la restauration réelle. Un fichier absent ou
vide est signalé explicitement ; les permissions trop ouvertes sont refusées. Une mauvaise clé
ou un fichier chiffré altéré provoque un refus avant remplacement des données.

Après déchiffrement, les confirmations et contrôles sont ceux de la procédure standard.
La sauvegarde de secours est également chiffrée avec cette clé et accompagnée d'un SHA-256.
Les données existent temporairement en clair dans un dossier root privé pendant l'opération.

Reprendre les contrôles client/SSH/services et le redémarrage du guide standard. Retirer
ensuite du VPS **la copie temporaire de la clé**, en conservant l'original et ses copies
de secours hors VPS. Ne pas effacer le coffre original ou la seule copie disponible.
