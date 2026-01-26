# Testování - Návod

## Spuštění testů

### Všechny testy
```bash
pytest tests/ -v
```

### S code coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Jeden konkrétní test
```bash
# Podle názvu testu
pytest tests/test_endpoint_config.py::test_endpoint_config_insert -v

# Podle části názvu (pattern matching)
pytest tests/ -k "endpoint_config_insert" -v

# Podle markeru
pytest tests/ -m "create" -v
pytest tests/ -m "crud" -v
pytest tests/ -m "endpoint_config" -v
```

### Pouze failed testy
```bash
pytest tests/ --lf  # last failed
pytest tests/ --ff  # failed first (nejdřív failed, pak ostatní)
```

### Pouze první failed test
```bash
pytest tests/ -x  # zastaví po prvním failu
pytest tests/ -x -v  # s verbose výpisem
```

### Podle kategorie
```bash
# Pouze CREATE operace
pytest tests/ -m "create" -v

# Pouze READ operace
pytest tests/ -m "read" -v

# Pouze UPDATE operace
pytest tests/ -m "update" -v

# Pouze DELETE operace
pytest tests/ -m "delete" -v

# Pouze validace
pytest tests/ -m "validation" -v

# Pouze error handling
pytest tests/ -m "error_handling" -v

# Pouze EndpointConfig testy
pytest tests/ -m "endpoint_config" -v

# Pouze ApiKey testy
pytest tests/ -m "api_key" -v
```

### Kombinace markerů
```bash
# CREATE operace pro EndpointConfig
pytest tests/ -m "create and endpoint_config" -v

# CRUD operace bez error handling
pytest tests/ -m "crud and not error_handling" -v
```

## Markery

Testy jsou automaticky označeny markery podle názvu:

- **CRUD kategorie:**
  - `crud` - všechny CRUD operace
  - `create` - CREATE operace
  - `read` - READ operace
  - `update` - UPDATE operace
  - `delete` - DELETE operace

- **Typy testů:**
  - `validation` - validace
  - `error_handling` - error handling
  - `filtering` - filtrování
  - `edge_cases` - edge cases

- **Entity:**
  - `endpoint_config` - EndpointConfig entity
  - `api_key` - ApiKey entity
  - `event` - Event entity
  - `user` - User entity
  - `document` - Document entity

## Výpis výsledků

### Základní výpis
```bash
pytest tests/ -v
```

### Detailní výpis s lokálními proměnnými
```bash
pytest tests/ -v --showlocals
```

### Krátký výpis (jen souhrn)
```bash
pytest tests/ -q
```

### Výpis všech (passed, failed, skipped)
```bash
pytest tests/ -ra
```

## Code Coverage

### HTML report
```bash
pytest tests/ --cov=src --cov-report=html
# Otevřít: htmlcov/index.html
```

### Terminálový výpis
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

### XML report (pro CI/CD)
```bash
pytest tests/ --cov=src --cov-report=xml
```

## Příklady

### Spustit jeden konkrétní test s detailním výpisem
```bash
pytest tests/test_endpoint_config.py::test_endpoint_config_insert -v --showlocals
```

### Spustit všechny CREATE testy a zastavit po prvním failu
```bash
pytest tests/ -m "create" -x -v
```

### Spustit všechny EndpointConfig testy s coverage
```bash
pytest tests/ -m "endpoint_config" --cov=src --cov-report=term-missing
```

### Spustit pouze failed testy z předchozího běhu
```bash
pytest tests/ --lf -v
```
