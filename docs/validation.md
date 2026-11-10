# Check-list de restauration réelle

Les commandes sont dans le [guide de restauration](restoration.md). Utiliser un VPS et des
clients de test, sans exposer une copie de la PKI de production sur un réseau actif.

- Debian 13 AMD64 préparé complètement avec radio-vpn radio-v2.4 ; nouvelle connexion SSH par clé validée.
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
