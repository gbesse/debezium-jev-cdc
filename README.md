# Debezium Jev CDC

Experimental community alpha v0.1.0 · MIT · Python 3.11+.

## Français

Ce consommateur JSONL transforme les enveloppes de changement Debezium en événements de décision Jev. Il réévalue seulement les textes modifiés, conserve un état SQLite local et émet un identifiant d'événement déterministe. Une suppression émet `delete` ; la tombstone qui suit est ignorée. Les lignes invalides vont dans un fichier de revue privé. Les événements de sortie ne contiennent pas le texte source.

Démonstration sans réseau :

```sh
mkdir -p .local
python3 cdc.py examples/changes.jsonl --fixtures examples/fixtures.json > .local/output.jsonl
python3 -m unittest discover -s tests -v
```

Pour Jev réel, omettre `--fixtures` et définir `TYPESAFE_API_KEY` dans l'environnement serveur. Acheminer stdout vers un consommateur idempotent : ce CLI ne gère ni Kafka ni ses acquittements. Le seuil `0.9` est illustratif. Évaluer des cas étiquetés avant toute action automatique.

## English

This JSONL consumer turns Debezium change envelopes into Jev decision events. It re-evaluates only changed text, keeps local SQLite state, and emits deterministic event IDs. A delete emits `delete`; the following tombstone is ignored. Invalid rows go to a private review file. Output events contain no source text.

Offline demo:

```sh
mkdir -p .local
python3 cdc.py examples/changes.jsonl --fixtures examples/fixtures.json > .local/output.jsonl
python3 -m unittest discover -s tests -v
```

For live Jev, omit `--fixtures` and set `TYPESAFE_API_KEY` in the server environment. Deliver stdout to an idempotent consumer: this CLI does not manage Kafka or acknowledgements. The `0.9` threshold is illustrative. Evaluate labeled cases before automated actions.

## Español

Este consumidor JSONL transforma envolturas de cambios de Debezium en eventos de decisión Jev. Reevalúa solo el texto modificado, guarda el estado local en SQLite y emite identificadores de evento deterministas. Una eliminación emite `delete`; se omite la tombstone siguiente. Las filas inválidas van a un archivo de revisión privado. Los eventos de salida no contienen el texto original.

Demostración sin red:

```sh
mkdir -p .local
python3 cdc.py examples/changes.jsonl --fixtures examples/fixtures.json > .local/output.jsonl
python3 -m unittest discover -s tests -v
```

Para Jev real, omite `--fixtures` y define `TYPESAFE_API_KEY` en el entorno del servidor. Envía stdout a un consumidor idempotente: este CLI no gestiona Kafka ni sus confirmaciones. El umbral `0.9` es ilustrativo. Evalúa casos etiquetados antes de automatizar acciones.

[Debezium transformations](https://debezium.io/documentation/reference/stable/transformations/index.html). Independent project, unaffiliated with Debezium or TypeSafe.
