# Prise en main des agents — NaviCapt

Ces consignes s’appliquent à l’ensemble de ce dépôt. Lire le [README](README.md), puis [agent/setup.md](agent/setup.md) pour l’installation et les procédures détaillées.

## Architecture

- `main.py` choisit le mode selon l’interpréteur : surveillance sur MicroPython, visualiseur USB sur Python PC ; `--simulation` ouvre la démo PC.
- `src/onboard_system.py` orchestre acquisition, calibration, décisions, météo et sorties.
- `src/drivers/` fournit les pilotes réels et simulés ; `src/functions/` sépare acquisition/calculs, décisions et commandes.
- `src/config.py` centralise GPIO, repères, seuils et périodes ; vérifier le montage avant de les changer.
- `src/run_log.py` écrit le journal ; `src/telemetry.py` définit les trames console `NAVICAPT`.
- `src/pico_viewer.py` et `src/boat_view.py` affichent les mesures ; `thonny_plugin/` observe les événements de console dans Thonny.

## Contrats à préserver

- `bome_deg` est la différence signée des caps bôme/bateau dans `[-180, 180[`, disponible dès la première acquisition ; `bome_zero_deg` est le zéro optionnel distinct.
- GP20 arme/calibre ; RUN–GND redémarre matériellement le Pico. Ne pas traiter RUN comme un GPIO logiciel.
- Les angles affichés avant armement ne signifient pas que la surveillance est active ; respecter `mesures_valides`, les défauts et les dates de mesure.
- Justifier les changements de seuils, d’hystérésis, de calibration ou de comportement d’alerte et vérifier les scénarios concernés.
- L’extension Thonny écoute passivement la console, sans ouvrir un second port USB ni supprimer les sorties.
- Conserver la validation des trames, les unités, le journal borné et le traitement des erreurs réseau/disque. Ne pas remplacer la météo réelle par des données inventées.
- Préserver la compatibilité MicroPython des chemins embarqués ; ne pas y importer Tkinter ni une dépendance réservée au PC.

## Sources et fichiers locaux

- Modifier les sources à la racine et dans `src/`, `thonny_plugin/`, `tools/` ; ne pas corriger uniquement une copie générée ou installée.
- `thonny_pico/` et son ZIP sont générés et ignorés par Git. Les régénérer après un changement embarqué avec `python3 tools/preparer_thonny.py`.
- L’installateur recopie aussi les modules graphiques partagés : après leur modification, une réinstallation puis un redémarrage de Thonny sont nécessaires pour les essayer dans l’extension.
- Garder les identifiants Wi-Fi, journaux, environnements et caches hors du dépôt. Ne pas écraser les logs du Pico lors d’un transfert.

## Vérification

Exécuter depuis la racine, avec les dépendances décrites dans le guide :

```sh
python3 -m unittest discover -s tests -v
# Suite graphique complète sous Linux, si Xvfb est disponible :
xvfb-run -a python3 -m unittest discover -s tests -v
```

Choisir les tests pertinents au changement ; une modification purement documentaire appelle surtout une vérification des liens et commandes. Signaler les tests ignorés, les limites de plateforme et la différence entre simulation/test PC et validation physique. Conserver les explications destinées à l’équipe en français et le README succinct ; placer les procédures détaillées dans `agent/setup.md`.
