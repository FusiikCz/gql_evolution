## Azure Proxy (LLM Reverse Proxy) – napojení na DB klíčů

### Co proxy dělá
- **Validuje API klíč** z hlavičky (`Authorization: Bearer ...` nebo `X-Api-Key: ...`) proti DB (prefix + hash compare)
- Kontroluje **is_active** + **expires_at**
- Vynucuje **rate limits** (minute/hour/day) a volitelné měsíční kvóty (tokens/cost)
- Po každém requestu zapisuje **usage** do DB (tokens, status, route, deployment, model, cost_usd) a aktualizuje `last_used_at`

### Důležité env proměnné
- `DATABASE_URL`: připojení k DB (default `sqlite+aiosqlite:///./proxy.db`)
- `API_KEY_PEPPER`: volitelný server-side pepper pro hashing tokenu
- `OPENAI_MODEL_PRICING_JSON`: JSON mapa pro výpočet `cost_usd` (USD per 1k tokens)
  - Příklad:
    - `{"gpt-4o-mini":{"prompt_per_1k":0.00015,"completion_per_1k":0.0006}}`

### Hlavičky klienta
- `Authorization: Bearer <PLAINTEXT_API_KEY>`
  - nebo `X-Api-Key: <PLAINTEXT_API_KEY>`

### Metriky
- `GET /metrics` – Prometheus metriky proxy:
  - `azure_proxy_requests_total{route,status}`
  - `azure_proxy_rate_limit_hits_total{route}`
  - `azure_proxy_tokens_total{route,kind}`

### Poznámka k DB schématu
Proxy používá vlastní tabulky (`users`, `api_keys`, `usage`) definované v `azure_proxy/db.py`.
Pokud chceš sdílet DB se zbytkem aplikace, je potřeba sjednotit schéma (nejen connection string).


