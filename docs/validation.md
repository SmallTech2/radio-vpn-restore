# Check-list de restauration réelle

Les commandes sont dans le [guide de restauration](restoration.md). Utiliser un VPS et des
clients de test, sans exposer une copie de la PKI de production sur un réseau actif.

- Debian 13 AMD64 préparé complètement avec radio-vpn, avec le réseau VPN de la sauvegarde ; nouvelle connexion SSH par clé validée.
- Archive et SHA-256 récupérés depuis le bon dossier NAS, sans dépendre du VPN à reconstruire.
- Installation de Git et clonage réalisés avec le compte Linux du nouveau VPS.
- Archive standard reconnue même sans age ; aucune demande de clé de déchiffrement.
- Confirmation de l'IP publique et du compte existant ; réseau restauré conforme et sans conflit de routes.
- Même empreinte CA, même certificat/série d'un ancien client, même IP fixe.
- Connexion de cet ancien client avec son profil initial, après changement de `remote` si nécessaire.
- Entrée de révocation conservée et essai d'un profil de test révoqué effectivement refusé.
- Création et connexion d'un nouveau client de test, sans collision de numéros de série ou d'IP.
- UI accessible par VPN ou tunnel SSH, avec les identifiants de la base sauvegardée.
- SSH, clés d'hôte et pare-feu de destination préservés ; nouvelle connexion SSH encore possible.
- Services, timers, réseau et clients contrôlés une nouvelle fois après redémarrage.
- Sauvegarde et collecte réinstallées/reconfigurées pour le nouveau VPS ; cycle automatique vérifié.
- Sur machine de test seulement : erreur après substitution, retour automatique à l'état précédent vérifié.
- Séparément, [archive age](encryption.md) : bonne clé acceptée, mauvaise clé/fichier altéré refusés,
  secours chiffré lisible avec la même clé, copie temporaire de clé retirée après validation.

Ces contrôles nécessitent de vrais VPS et le DSM utilisé. Les fixtures et simulations de
tests ne valident ni les services d'un hébergeur, ni les ACL/notifications/horaires DSM.
Conserver les sauvegardes d'origine tant que cette recette n'est pas terminée.

## Compatibilité et contrôle sans remplacement

Les tests couvrent une source radio-v2.1 sans fichiers facultatifs ni `crlnumber`, une
destination radio-v2.4, la conservation de la PKI et des versions/commits, ainsi que
l’absence de remplacement des configurations SSH, nftables et IPv6 de destination.
Les fichiers de logs absents de l’archive laissent ceux du nouveau VPS en place.
Le retour arrière rétablit aussi l’absence initiale d’un fichier facultatif.

Les refus testés comprennent : clé client incompatible, révocation manquante dans la
CRL, IP fixe dupliquée, réseau différent, composant obligatoire manquant, schéma SQLite
incompatible et parent de destination symbolique. Une simulation de l’assistant vérifie
que `--check`, réussi ou en échec, ne modifie aucun service ni configuration.

Sur le VPS de test, exécuter `sudo bash restore.sh --check "$ARCHIVE"`, confirmer l’IP
et le compte, puis vérifier les services et données inchangés. Restaurer ensuite et
suivre les essais client valide/révoqué et SSH. Les tests automatisés ne valident pas
une restauration réelle ni le fonctionnement après redémarrage.
