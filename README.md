# radio-vpn-restore

Restauration d'une sauvegarde [radio-vpn-backup](https://github.com/SmallTech2/radio-vpn-backup)
sur un VPS Debian 13 AMD64 préparé avec **radio-vpn radio-v2.4**. La PKI, les certificats,
révocations, IP fixes et comptes Web sont conservés ; aucune nouvelle CA n'est générée
par cet outil. La CRL est remise à jour sans renouveler les certificats.

## Première restauration

Suivre le [guide complet](docs/restoration.md) depuis le VPS vierge : préparation radio-vpn,
récupération de l'archive sur le Synology, transfert depuis le poste administrateur,
installation, assistant et contrôles avant/après redémarrage. Chaque commande indique
sa machine, son compte et comment obtenir les chemins réels.

## Restauration d'urgence

**Nouveau VPS — compte administrateur Linux avec sudo.** Prérequis : radio-vpn radio-v2.4
entièrement installé, SSH par clé vérifié, archive `.tar.gz` et `.sha256` déjà copiées dans
un dossier privé. Si ces prérequis manquent, commencer par le guide complet.

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/SmallTech2/radio-vpn-restore.git "$HOME/radio-vpn-restore"
cd "$HOME/radio-vpn-restore"
read -r -p 'Chemin absolu de l archive copiée sur ce VPS : ' ARCHIVE
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$ARCHIVE").sha256")
gzip -t "$ARCHIVE"
sudo bash restore.sh
```

Si le dépôt existe déjà, utiliser son dossier propre et `git pull --ff-only` au lieu de
le cloner à nouveau. Ne poursuivre qu'après réussite des contrôles. Donner au script le
chemin de l'archive, confirmer l'IP publique et le compte existant, puis taper `RESTAURER`.
**Le mode standard ne demande ni age ni clé de déchiffrement.**

## Guides et limites

- [Procédure complète, depuis Debian 13 vierge](docs/restoration.md).
- [Option : restaurer une archive chiffrée avec age](docs/encryption.md).
- [Erreur, sauvegarde de secours et retour arrière](docs/recovery.md).
- [Check-list de validation réelle](docs/validation.md).

Les archives standard ne sont pas chiffrées et contiennent notamment la clé privée de
la CA et les clés clients : ce choix est volontaire et son risque accepté. Stocker les
fichiers en privé et ne jamais les publier. SHA-256 n'est pas une signature d'auteur.

La restauration interrompt le VPN de destination. Si l'IP publique change, les profils
déjà distribués nécessitent l'adaptation de `remote`, sans renouveler leurs certificats.
Les accès SSH, clés d'hôte et pare-feu du nouveau VPS sont conservés. Les tests automatisés
ne remplacent pas une recette réelle VPS/DSM ; aucune Release des outils n'est publiée.

## Licence

[MIT](LICENSE). Outil compagnon de Radio Bonheur pour radio-vpn, dérivé de
[d3vilh/openvpn-ui](https://github.com/d3vilh/openvpn-ui), avec les attributions conservées.
