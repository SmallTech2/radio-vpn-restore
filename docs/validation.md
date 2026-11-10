# Recette de sauvegarde et restauration

Sur des machines de test uniquement, sans reutiliser une PKI de production dans un reseau actif :

1. Installer radio-vpn radio-v2.4, creer deux clients a IP fixes, revoquer l'un d'eux.
2. Noter les empreintes CA/serveur/client, numeros de serie, IP fixes et entree R.
3. Lancer une sauvegarde pendant qu'un client valide est connecte : verifier qu'il reste connecte.
4. Recuperer depuis DSM par le compte restreint. Tester un refus de shell, de transfert de ports,
   de lecture arbitraire et d'ecriture. Verifier SHA-256, gzip et les permissions des archives non chiffrees.
5. Tester disque plein, archive corrompue, transfert interrompu et NAS temporairement indisponible :
   aucune archive incomplete ne doit etre visible, les anciennes doivent rester utilisables.
6. Preparer un autre VPS Debian 13 avec radio-vpn ; suivre le README de radio-vpn-restore.
7. Comparer les empreintes et IP fixes. La CRL peut avoir une nouvelle date, mais l'entree R reste presente.
8. Adapter `remote` sur le client de test si l'IP publique change ; verifier la connexion avec son certificat initial.
9. Verifier que le certificat revoque est refuse. Creer un nouveau client, lui affecter une IP et verifier sa connexion.
10. Tester SSH, UI via tunnel et VPN, nftables, timers, puis redemarrer le VPS de test et recommencer les controles.
11. Simuler un echec apres remplacement : verifier le retour arriere des donnees et des services et la preservation SSH.

Ne pas faire fonctionner deux serveurs issus de la meme PKI comme deux autorites independantes :
leurs index/serials pourraient diverger. Pour une bascule planifiee, arreter les ecritures sur
l'ancien serveur, faire une derniere sauvegarde, puis le maintenir hors service apres bascule.

Ces controles sur VPS/DSM restent a realiser. Les fixtures automatiques ne valident pas
les reseaux d'un hebergeur, la console, le redemarrage reel ou une restauration de production.

Tester les deux modes : ENCRYPT=false sans age, puis ENCRYPT=true avec une cle generee
hors du VPS. Verifier la collecte et la retention d'un ensemble mixte, la detection du
format a la restauration, le refus d'une mauvaise cle et le chiffrement du secours
lorsque l'archive restauree est chiffree. Le mode standard ne doit jamais demander de cle.
