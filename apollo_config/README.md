# Apollo Router Setup

Tento adresář obsahuje konfiguraci pro Apollo Router - GraphQL Federation Gateway.

## Rychlý start

1. **Spusť Docker Compose služby:**
   ```powershell
   docker-compose up -d gql_app
   ```

2. **Vygeneruj supergraph schema:**
   ```powershell
   docker-compose run --rm apollo_rover
   ```
   Tento příkaz vytvoří `supergraph.graphql` soubor pomocí rover CLI v Docker kontejneru (funguje i na Windows!).

3. **Spusť Apollo Router:**
   ```powershell
   docker-compose up -d apollo_router
   ```

4. **Otestuj Apollo Router:**
   ```powershell
   # PowerShell příkaz:
   Invoke-WebRequest -Uri "http://localhost:4000" -Method POST -ContentType "application/json" -Body '{"query":"{ __typename }"}' | Select-Object -ExpandProperty Content
   
   # Nebo použij curl.exe (pokud je nainstalovaný):
   curl.exe http://localhost:4000 -X POST -H "Content-Type: application/json" -d '{\"query\":\"{ __typename }\"}'
   ```

## Struktura souborů

- `router.yaml` - Konfigurace Apollo Routeru (CORS, server nastavení)
- `supergraph.yaml` - Konfigurace pro rover CLI (definuje subgraphy)
- `supergraph.graphql` - Vygenerovaný supergraph schema (vytvoří se pomocí `apollo_rover` služby)
- `Dockerfile.rover` - Dockerfile pro rover CLI kontejner
- `generate_supergraph.sh` - Skript pro generování supergraph schema

## Jak to funguje?

1. **Rover CLI v Dockeru**: Místo instalace rover CLI lokálně (což má problémy na Windows), používáme Docker kontejner s rover CLI. To funguje na všech platformách.

2. **Generování supergraph**: `apollo_rover` služba se připojí k běžícímu `gql_app` a vygeneruje `supergraph.graphql` soubor.

3. **Apollo Router**: Apollo Router načte `supergraph.graphql` a `router.yaml` a poskytuje federovaný GraphQL endpoint na portu 4000.

## Obnovení supergraph schema

Pokud změníš GraphQL schéma v `gql_app`, musíš znovu vygenerovat supergraph:

```powershell
docker-compose run --rm apollo_rover
docker-compose restart apollo_router
```

## Alternativní přístup (pouze GraphQL endpoint)

Pokud nepotřebuješ Apollo Router, můžeš používat GraphQL endpoint přímo:
- `http://localhost:8000/gql` - Přímý GraphQL endpoint

Apollo Router je užitečný hlavně když máš více GraphQL služeb a chceš je federovat do jednoho endpointu.
