# Restaurer une archive chiffrée avec age

Cette option complète la [procédure de restauration](restoration.md). Une `.tar.gz`
standard ne demande ni age ni clé. Utiliser la paire native créée avec `age-keygen`
selon le [guide de sauvegarde chiffrée](https://github.com/SmallTech2/radio-vpn-backup/blob/main/docs/encryption.md).
La clé SSH du NAS ou du compte administrateur n’est pas cette clé de déchiffrement.

## Rassembler et préparer

Récupérer l’archive `.tar.gz.age` et ses empreintes depuis ABB ou le collecteur,
transférer les fichiers puis effectuer l’étape SHA-256 du guide principal. Ne pas
appliquer `gzip -t` au fichier chiffré.

Retrouver la clé privée age dans son coffre ou support hors ligne. Ne pas en générer
une nouvelle : elle ne déchiffrerait pas les archives existantes. Transférer une copie
avec le SFTP du **compte administrateur du nouveau VPS**, dans le dossier privé
`$HOME/sauvegardes-radio`, et garder l’original hors du VPS.

**Nouveau VPS — même administrateur :**

```bash
sudo apt update
sudo apt install -y age
read -r -p 'Chemin absolu de la copie locale de clé privée age : ' AGE_KEY
chmod 600 "$AGE_KEY"
printf 'Chemin à indiquer à l assistant : %s\n' "$AGE_KEY"
```

Le chemin est celui du fichier réellement transféré, pas un exemple. Ne pas afficher
son contenu. Reprendre ensuite les étapes de clonage et de contrôle du guide principal.

## Contrôler puis restaurer

Dans le clone radio-vpn-restore, avec `ARCHIVE` désignant le fichier chiffré :

```bash
sudo bash restore.sh --check "$ARCHIVE"
```

Le script reconnaît le contenu et demande le chemin de la clé privée une fois pour
cette exécution. Il refuse une clé absente, vide, incorrecte ou aux permissions trop
ouvertes ; une archive altérée est également refusée avant remplacement.

Après réussite, lancer `sudo bash restore.sh` et suivre le guide principal. Chaque
exécution demande à nouveau les renseignements nécessaires : aucun cache de clé n’est
créé. Dans la restauration réelle, la clé choisie sert aussi à chiffrer le secours local,
sans nouvelle saisie. Les copies de travail sont temporairement en clair dans un dossier
root privé, supprimé à la fin normale du script.

Après remise en service, retirer du VPS uniquement la copie temporaire de clé, en
conservant l’original et ses copies de secours hors VPS. Garder le secours chiffré et son
SHA-256 tant qu’ils sont nécessaires ; ne pas effacer la seule clé disponible.
