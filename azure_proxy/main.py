import os
import json
import hashlib
import asyncio
import time
import logging
from typing import Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from .db import (
    AsyncSessionMaker,
    require_api_key,
    check_rate_limits,
    record_usage,
    ApiKeyAuthError,
    ApiKey,
    init_db,
)

import prometheus_client
from prometheus_client import Counter

# ==== Konfigurace z env ====
UPSTREAM_ACCOUNT = os.getenv("AZURE_COGNITIVE_ACCOUNT_NAME", "")
UPSTREAM_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
UPSTREAM_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
UPSTREAM_ENDPOINT = f"https://{UPSTREAM_ACCOUNT}.openai.azure.com"

PROXY_BIND = os.getenv("PROXY_BIND", "0.0.0.0")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8787"))

PROXY_TOKEN = os.getenv("PROXY_TOKEN", "")  # volitelné – pokud je nastaveno, vyžaduje X-Proxy-Token
LOG_PROMPTS = os.getenv("PROXY_LOG_PROMPTS", "false").lower() == "true"
FORCE_JSON_RESPONSE = os.getenv("FORCE_JSON_RESPONSE", "false").lower() == "true"
TIMEOUT_SECS = float(os.getenv("UPSTREAM_TIMEOUT", "60"))


# --- NOVÉ ENV pro OpenAI-compatible režim ---
OPENAI_COMPAT_ENABLED = os.getenv("OPENAI_COMPAT_ENABLED", "true").lower() == "true"
# JSON mapa: "openai_model" -> "azure_deployment"
# např: {"gpt-4o":"gpt4o-prod","gpt-4o-mini":"gpt4o-mini"}
OPENAI_COMPAT_MODEL_MAP = os.getenv("OPENAI_COMPAT_MODEL_MAP", "{}")

try:
    MODEL_MAP: dict[str, str] = json.loads(OPENAI_COMPAT_MODEL_MAP) if OPENAI_COMPAT_MODEL_MAP else {}
except Exception:
    MODEL_MAP = {
        "gpt-5-nano": "gpt-5-nano",
        "gpt-4.1": "orchestration-deployment",
        "gpt-4o-mini": "summarization-deployment",
    }

# region Usage Logs
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEFAULT_DEPLOYMENT", "summarization-deployment")  # fallback, když model není v mapě

USAGE_LOG_PATH = os.getenv("USAGE_LOG_PATH", "")  # když nastavíš cestu, zapisuje se JSONL
USAGE_LOG_STDOUT = os.getenv("USAGE_LOG_STDOUT", "true").lower() == "true"

_usage_lock = asyncio.Lock()
def _now_iso():
    import datetime as _dt
    # Return ISO 8601 timestamp in UTC with 'Z' suffix (e.g., "2024-01-15T10:30:00Z")
    # Remove timezone info before isoformat to avoid +00:00Z (invalid format)
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"

async def log_usage_record(record: dict):
    """Zapíše jednu řádku s usage do JSONL + volitelně na stdout."""
    line = json.dumps(record, ensure_ascii=False)
    if USAGE_LOG_STDOUT:
        print(f"[USAGE] {line}")
    if USAGE_LOG_PATH:
        async with _usage_lock:
            with open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    return record

def make_usage_record(
    *,
    route: str,
    request: Request | None,
    deployment: str | None,
    # model: str | None,
    stream: bool,
    status: int | None,
    usage: dict | None,
    idempotency_key: str | None,
    upstream_headers: dict | None = None,
    extra: dict | None = None,
) -> dict:
    rec = {
        "ts": _now_iso(),
        "route": route,
        "deployment": deployment,
        # "model": model,
        "stream": bool(stream),
        "status": status,
        "usage": usage or {},
        "idempotency_key": idempotency_key,
        "client_ip": getattr(request.client, "host", None) if request else None,
        "req_x_request_id": request.headers.get("X-Request-Id") if request else None,
    }
    if upstream_headers:
        # Azure/OpenAI často vrací X-Request-Id, X-Ratelimit*, apod.
        rec["upstream_request_id"] = upstream_headers.get("x-request-id") or upstream_headers.get("X-Request-Id")
        rec["ratelimit_remaining_tokens"] = upstream_headers.get("x-ratelimit-remaining-tokens")
        rec["ratelimit_limit_tokens"] = upstream_headers.get("x-ratelimit-limit-tokens")
    if extra:
        rec.update(extra)
    return rec


# endregion

# region Pricing (cost_usd)
OPENAI_MODEL_PRICING_JSON = os.getenv("OPENAI_MODEL_PRICING_JSON", "")
try:
    # { "gpt-4o-mini": {"prompt_per_1k": 0.00015, "completion_per_1k": 0.0006}, ... }
    MODEL_PRICING: dict[str, dict[str, float]] = json.loads(OPENAI_MODEL_PRICING_JSON) if OPENAI_MODEL_PRICING_JSON else {}
except Exception:
    MODEL_PRICING = {}

def compute_cost_usd(*, model: str | None, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    if not model:
        return None
    p = MODEL_PRICING.get(model)
    if not p:
        return None
    pt = prompt_tokens or 0
    ct = completion_tokens or 0
    try:
        return (pt * float(p.get("prompt_per_1k", 0.0)) + ct * float(p.get("completion_per_1k", 0.0))) / 1000.0
    except Exception:
        return None
# endregion

# region Metrics (Prometheus)
PROXY_REQUESTS_TOTAL = Counter(
    "azure_proxy_requests_total",
    "Total proxied requests",
    ["route", "status"],
)
PROXY_RATE_LIMIT_HITS_TOTAL = Counter(
    "azure_proxy_rate_limit_hits_total",
    "Requests rejected by proxy rate limits",
    ["route"],
)
PROXY_TOKENS_TOTAL = Counter(
    "azure_proxy_tokens_total",
    "Total tokens observed in OpenAI/Azure usage payload",
    ["route", "kind"],  # prompt|completion|total
)

# Additional metrics for endpoint tracking
PROXY_ENDPOINT_REQUESTS_TOTAL = Counter(
    "azure_proxy_endpoint_requests_total",
    "Total number of requests per endpoint configuration",
    ["endpoint_config_id", "route", "status"]
)

PROXY_ENDPOINT_COST_TOTAL = Counter(
    "azure_proxy_endpoint_cost_total",
    "Total cost per endpoint configuration in USD",
    ["endpoint_config_id", "route"]
)
# endregion


# --- POMOCNÉ FUNKCE PRO OPENAI KOMPAT ---
def resolve_deployment_from_model(model_name: str) -> str:
    """
    Přeloží OpenAI model (např. 'gpt-4o') na Azure deployment (např. 'gpt4o-prod').
    Fallback: DEFAULT_DEPLOYMENT.
    """
    dep = MODEL_MAP.get(model_name)
    if not dep:
        dep = DEFAULT_DEPLOYMENT
    if not dep:
        # nechceme spadnout; ať je chyba čitelná
        raise HTTPException(
            status_code=400, 
            detail=(
                f"No deployment mapped for model '{model_name}'. "
                "\n"
                f"model map: {json.dumps(MODEL_MAP, indent=1)}"
                "\n"
                f"Provide OPENAI_COMPAT_MODEL_MAP or AZURE_OPENAI_DEFAULT_DEPLOYMENT."
            )
        )
    return dep

def azure_chat_url(deployment: str) -> str:
    return f"{UPSTREAM_ENDPOINT}/openai/deployments/{deployment}/chat/completions?api-version={UPSTREAM_API_VERSION}"

def azure_responses_url(deployment: str) -> str:
    return f"{UPSTREAM_ENDPOINT}/openai/deployments/{deployment}/responses?api-version={UPSTREAM_API_VERSION}"



# ==== HTTP klient ====
client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_SECS, connect=10.0))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database connection
    await init_db()
    yield
    await client.aclose()

app = FastAPI(
    title="Azure OpenAI Reverse Proxy",
    lifespan=lifespan
)

async def require_auth(request: Request):
    if PROXY_TOKEN:
        token = request.headers.get("X-Proxy-Token")
        if token != PROXY_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

def redact(s: str, keep: int = 4) -> str:
    if not s: return ""
    return s[:keep] + "…" if len(s) > keep else "****"

async def _extract_client_api_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    api_key = request.headers.get("X-Api-Key") or request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    return None

async def require_client_api_key(request: Request) -> ApiKey:
    """
    Ověří klientský API klíč proti DB a zkontroluje limity.
    Klíč uloží do request.state.api_key pro pozdější použití.
    """
    token = await _extract_client_api_token(request)
    key = None
    async with AsyncSessionMaker() as db:
        try:
            key = await require_api_key(db, token)
            await check_rate_limits(db, api_key=key)
        except ApiKeyAuthError as e:
            # mapuj na HTTP kódy
            msg = str(e) or "Unauthorized"
            status = 429 if "limit" in msg.lower() or "quota" in msg.lower() or "exceeded" in msg.lower() else 401
            if status == 429:
                PROXY_RATE_LIMIT_HITS_TOTAL.labels(route=request.url.path).inc()
            raise HTTPException(status_code=status, detail=msg)
    
    # Only set and return key if authentication succeeded
    if key is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    request.state.api_key = key
    return key

def gen_idempotency_key(body: dict) -> str:
    # deterministicky z modelu + messages + function/tool calls …
    canonical = json.dumps(
        {k: body.get(k) for k in ("model", "messages", "tools", "tool_choice", "response_format", "temperature")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]

async def backoff_delays(max_retries: int = 3):
    # 0.5s, 1s, 2s (+ jitter)
    base = 0.5
    for i in range(max_retries):
        delay = base * (2 ** i)
        yield delay + (0.05 * (i + 1))

def build_upstream_url(deployment: str) -> str:
    return f"{UPSTREAM_ENDPOINT}/openai/deployments/{deployment}/chat/completions?api-version={UPSTREAM_API_VERSION}"

def maybe_force_json_response(body: dict) -> dict:
    if FORCE_JSON_RESPONSE:
        rf = body.get("response_format")
        if not isinstance(rf, dict) or rf.get("type") not in ("json_object", "json_schema"):
            body["response_format"] = {"type": "json_object"}
    return body

def log_req(deployment: str, body: dict):
    meta = {k: body.get(k) for k in ("model","temperature","stream")}
    if LOG_PROMPTS:
        # POZOR: může obsahovat PII
        print(f"[REQ] dep={deployment} meta={meta} messages={json.dumps(body.get('messages', [])[:2], ensure_ascii=False)[:500]}…")
    else:
        # bezpečné minimum
        print(f"[REQ] dep={deployment} meta={meta} messages_count={len(body.get('messages', []))}")

def log_res(status: int, usage: Optional[dict]):
    print(f"[RES] status={status} usage={usage or {}}")

def extract_usage(json_obj: dict) -> Optional[dict]:
    if not isinstance(json_obj, dict):
        return None
    return (
        json_obj.get("usage")
        or (json_obj.get("response") or {}).get("usage")
        or (json_obj.get("output") or {}).get("usage")
    )

def upstream_headers(request: Request, idemp: str | None) -> dict:
    # klient nemusí posílat Azure API key; proxy vloží vlastní
    h = {
        "api-key": UPSTREAM_API_KEY,
        "Content-Type": "application/json",
    }
    # Idempotency-Key (Azure jej akceptuje; OpenAI standard taky)
    if idemp:
        h["Idempotency-Key"] = idemp
    # Forward-X pro audit
    if request.headers.get("X-Request-Id"):
        h["X-Request-Id"] = request.headers["X-Request-Id"]
    return h

async def forward_nonstream(
    request: Request,
    deployment: str,
    url: str, 
    headers: dict, 
    body: dict, 
    idempotency_key: str,
    routelabel: str="unknown",
    api_key: ApiKey | None = None,
) -> Response:
    # non-stream s retry
    last_exc = None
    for delay in [0.0, *[d async for d in backoff_delays(3)]]:
        if delay:
            await asyncio.sleep(delay)
        try:
            r = await client.post(url, headers=headers, json=body)
            if not should_retry(r.status_code):
                try:
                    data = r.json()
                except Exception:
                    data = None
                usage = extract_usage(data or {})
                try:
                    PROXY_REQUESTS_TOTAL.labels(route=routelabel, status=str(r.status_code)).inc()
                except Exception:
                    pass
                usage_record = make_usage_record(
                    route=routelabel,
                    request=request,
                    deployment=deployment,
                    stream=False,
                    status=r.status_code,
                    usage=usage,
                    # route=routelabel,
                    idempotency_key=idempotency_key,
                    upstream_headers=r.headers
                )
                await log_usage_record(usage_record)
                # Persist usage do DB
                if api_key is not None:
                    try:
                        model_name = body.get("model") or deployment
                        pt = (usage or {}).get("prompt_tokens")
                        ct = (usage or {}).get("completion_tokens")
                        tt = (usage or {}).get("total_tokens")
                        if isinstance(pt, int):
                            PROXY_TOKENS_TOTAL.labels(route=routelabel, kind="prompt").inc(pt)
                        if isinstance(ct, int):
                            PROXY_TOKENS_TOTAL.labels(route=routelabel, kind="completion").inc(ct)
                        if isinstance(tt, int):
                            PROXY_TOKENS_TOTAL.labels(route=routelabel, kind="total").inc(tt)
                        cost_usd = compute_cost_usd(
                            model=model_name,
                            prompt_tokens=pt if isinstance(pt, int) else None,
                            completion_tokens=ct if isinstance(ct, int) else None,
                        )
                        async with AsyncSessionMaker() as db:
                            usage_record = await record_usage(
                                db,
                                api_key=api_key,
                                route=routelabel,
                                deployment=deployment,
                                model=model_name,
                                status=r.status_code,
                                stream=False,
                                prompt_tokens=pt if isinstance(pt, int) else None,
                                completion_tokens=ct if isinstance(ct, int) else None,
                                total_tokens=tt if isinstance(tt, int) else None,
                                stream_bytes=None,
                                cost_usd=cost_usd,
                                meta={"idempotency_key": idempotency_key},
                                base_url=UPSTREAM_ENDPOINT,  # Auto-detect endpoint_config_id
                            )
                            # Increment endpoint-specific metrics if endpoint_config_id was found
                            if usage_record and usage_record.endpoint_config_id:
                                try:
                                    PROXY_ENDPOINT_REQUESTS_TOTAL.labels(
                                        endpoint_config_id=str(usage_record.endpoint_config_id),
                                        route=routelabel,
                                        status=str(r.status_code)
                                    ).inc()
                                    if cost_usd:
                                        PROXY_ENDPOINT_COST_TOTAL.labels(
                                            endpoint_config_id=str(usage_record.endpoint_config_id),
                                            route=routelabel
                                        ).inc(cost_usd)
                                except Exception:
                                    pass  # Ignore metric errors
                    except Exception as _e:
                        logger.warning(f"Error recording usage to database: {type(_e).__name__}: {_e}", exc_info=True)
                log_res(r.status_code, usage=usage)
                if data is not None:
                    return JSONResponse(status_code=r.status_code, content=data)
                return PlainTextResponse(status_code=r.status_code, content=r.text)
            else:
                last_exc = f"Upstream status {r.status_code}, retrying…"
        except httpx.HTTPError as e:
            last_exc = f"HTTP error: {e}"
    raise HTTPException(status_code=502, detail=f"Upstream failed after retries: {last_exc}")

# async def stream_generator(url: str, headers: dict, body: dict):
#     async with client.stream("POST", url, headers=headers, json=body) as r:
#         async for chunk in r.aiter_bytes():
#             yield chunk

# async def forward_stream(url: str, headers: dict, body: dict) -> Response:
#     # zachovej event-stream
#     return StreamingResponse(stream_generator(url, headers, body), media_type="text/event-stream")


async def forward_stream_with_usage(
    url: str, 
    headers: dict, 
    body: dict, 
    *,
    route: str, 
    request: Request, 
    deployment: str | None,
    # model: str | None, 
    idempotency_key: str | None,
    parse_responses_usage: bool,
    api_key: ApiKey | None = None,
):
    async def _gen():
        usage_holder = None
        usage_counter = 0
        status_code = None
        upstream_headers = {}
        text_buf = ""

        async with client.stream("POST", url, headers=headers, json=body) as r:
            status_code = r.status_code
            upstream_headers = dict(r.headers)

            async for chunk in r.aiter_bytes():
                # pošli dál
                usage_counter += len(chunk)
                yield chunk

                if not parse_responses_usage:
                    continue

                # zkus poskládat SSE bloky a číst "data: {...}"
                try:
                    text_buf += chunk.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                while "\n\n" in text_buf:
                    block, text_buf = text_buf.split("\n\n", 1)
                    for line in block.splitlines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        try:
                            evt = json.loads(payload)
                        except Exception:
                            continue
                        # OpenAI/Azure Responses: zakončovací event nese usage
                        if isinstance(evt, dict) and evt.get("type") == "response.completed":
                            usage_holder = (evt.get("response") or {}).get("usage") or evt.get("usage") or {"usage_counter": usage_counter}

        # zapiš usage/metu po skončení streamu
        try:
            await log_usage_record(
                make_usage_record(
                    route=route, 
                    request=request, 
                    deployment=deployment, 
                    # model=model,
                    stream=True, 
                    status=status_code, 
                    usage=usage_holder,
                    idempotency_key=idempotency_key, 
                    upstream_headers=upstream_headers
                )
            )
            if api_key is not None:
                try:
                    model_name = body.get("model") or deployment
                    pt = (usage_holder or {}).get("prompt_tokens") if isinstance(usage_holder, dict) else None
                    ct = (usage_holder or {}).get("completion_tokens") if isinstance(usage_holder, dict) else None
                    tt = (usage_holder or {}).get("total_tokens") if isinstance(usage_holder, dict) else None
                    if isinstance(pt, int):
                        PROXY_TOKENS_TOTAL.labels(route=route, kind="prompt").inc(pt)
                    if isinstance(ct, int):
                        PROXY_TOKENS_TOTAL.labels(route=route, kind="completion").inc(ct)
                    if isinstance(tt, int):
                        PROXY_TOKENS_TOTAL.labels(route=route, kind="total").inc(tt)
                    cost_usd = compute_cost_usd(
                        model=model_name,
                        prompt_tokens=pt if isinstance(pt, int) else None,
                        completion_tokens=ct if isinstance(ct, int) else None,
                    )
                    async with AsyncSessionMaker() as db:
                        usage_record = await record_usage(
                            db,
                            api_key=api_key,
                            route=route,
                            deployment=deployment,
                            model=model_name,
                            status=status_code,
                            stream=True,
                            prompt_tokens=pt if isinstance(pt, int) else None,
                            completion_tokens=ct if isinstance(ct, int) else None,
                            total_tokens=tt if isinstance(tt, int) else None,
                            stream_bytes=usage_counter,
                            cost_usd=cost_usd,
                            meta={"idempotency_key": idempotency_key},
                            base_url=UPSTREAM_ENDPOINT,  # Auto-detect endpoint_config_id
                        )
                        # Increment endpoint-specific metrics if endpoint_config_id was found
                        if usage_record and usage_record.endpoint_config_id:
                            try:
                                PROXY_ENDPOINT_REQUESTS_TOTAL.labels(
                                    endpoint_config_id=str(usage_record.endpoint_config_id),
                                    route=route,
                                    status=str(status_code)
                                ).inc()
                                if cost_usd:
                                    PROXY_ENDPOINT_COST_TOTAL.labels(
                                        endpoint_config_id=str(usage_record.endpoint_config_id),
                                        route=route
                                    ).inc(cost_usd)
                            except Exception:
                                pass  # Ignore metric errors
                except Exception as _e:
                    logger.warning(f"Error recording usage to database: {type(_e).__name__}: {_e}", exc_info=True)
        except Exception as _e:
            logger.warning(f"Error processing usage data: {type(_e).__name__}: {_e}", exc_info=True)

    return StreamingResponse(
        _gen(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

def should_retry(status: int) -> bool:
    return status in (429, 500, 502, 503, 504)



async def openai_v1_chat_completions_general(
    request: Request, 
    useforce: bool, 
    deployment: str = None,
    endpoint: str = "chat",
    routelabel: str=""
):
    """
    Přijme OpenAI styl (model=..., messages=[...]) a přesměruje na Azure chat/completions.
    """
    if not OPENAI_COMPAT_ENABLED:
        raise HTTPException(status_code=404, detail="OpenAI-compatible mode disabled")

    await require_auth(request)
    # Vyžaduj klientský API klíč a limity
    api_key = await require_client_api_key(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model")
    if model:
        deployment = resolve_deployment_from_model(model)    
    elif deployment is None:
        raise HTTPException(status_code=400, detail="Missing 'model' (or explicit deployment)")
    
    if useforce and endpoint == "chat":
        body = maybe_force_json_response(body)  # volitelný forcing JSON output
    idempotency_key = request.headers.get("Idempotency-Key") or gen_idempotency_key(body)

    # Log a hlavičky (vezmeme Azure api-key, ne Authorization)
    log_req(f"OPENAI {routelabel} -> {deployment}", body)
    # headers = {
    #     "api-key": UPSTREAM_API_KEY,
    #     "Content-Type": "application/json",
    #     "Idempotency-Key": idemp,
    # }
    headers = upstream_headers(request, idempotency_key)
    if endpoint == "responses":
        url = azure_responses_url(deployment)
    else:
        # url = azure_chat_url(deployment)
        url = build_upstream_url(deployment)

    # stream?
    if body.get("stream"):
        return await forward_stream_with_usage(
            url, 
            headers, 
            body,
            request=request,
            route=routelabel,
            deployment=deployment,
            idempotency_key=idempotency_key,
            parse_responses_usage=True,
            api_key=api_key
        )
    return await forward_nonstream(
        request=request,
        deployment=deployment,
        url=url,
        headers=headers,
        body=body,
        idempotency_key=idempotency_key,
        routelabel=routelabel,
        api_key=api_key
    )

# ============= ROUTES =============

@app.post("/openai/deployments/{deployment}/chat/completions")
async def chat_completions(deployment: str, request: Request):
    return await openai_v1_chat_completions_general(
        request=request,
        useforce=True,
        deployment=deployment,
        endpoint="chat",
        routelabel="chat_completions",
    ) 

# ---------- OpenAI-compatible: /v1/models ----------
@app.get("/v1/models")
@app.get("/models")  # volitelně alias
async def list_models_openai():
    """
    Vrátí seznam 'modelů' podle klíčů v OPENAI_COMPAT_MODEL_MAP.
    OpenAI vrací object=list a položky s object=model.
    """
    items = []
    for mid in (MODEL_MAP.keys() or []):
        items.append({"id": mid, "object": "model", "created": 0, "owned_by": "azure-proxy"})
    # fallback: když není mapa, ale je DEFAULT_DEPLOYMENT, ukaž aspoň 1 id
    if not items and DEFAULT_DEPLOYMENT:
        items = [{"id": "gpt-azure", "object": "model", "created": 0, "owned_by": "azure-proxy"}]
    result = {"object": "list", "data": items}
    print(f"list_models_openai: {json.dumps(result, indent=2)}")
    return result

# ---------- OpenAI-compatible: /v1/chat/completions ----------
@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def openai_v1_chat_completions(request: Request):
    """
    Přijme OpenAI styl (model=..., messages=[...]) a přesměruje na Azure chat/completions.
    """
    return await openai_v1_chat_completions_general(
        request=request,
        useforce=True,
        endpoint="chat",
        routelabel="openai_v1_chat_completions"
    )

# ---------- OpenAI-compatible: /v1/responses ----------
@app.post("/v1/responses")
@app.post("/responses")
async def openai_v1_responses(request: Request):
    """
    OpenAI Responses API (model=..., input=[...]).
    Přesměruje na Azure /responses (2024-12-01-preview a novější).
    """
    return await openai_v1_chat_completions_general(
        request=request,
        useforce=False,
        endpoint="responses",
        routelabel="openai_v1_responses"
    )
    

@app.get("/healthcheck")
async def healthcheck():
    return {"ok": True}

@app.get("/metrics")
async def metrics():
    return Response(
        content=prometheus_client.generate_latest(),
        media_type=prometheus_client.CONTENT_TYPE_LATEST,
    )

@app.post("/llmtest/{deployment}")
async def llmtest(
    deployment: str,
    query: str
):
    
    from openai import AzureOpenAI, AsyncAzureOpenAI
    from openai.types.chat import ChatCompletion
    from openai.resources.chat.completions import AsyncCompletions
    client = AsyncAzureOpenAI(
        azure_endpoint=UPSTREAM_ENDPOINT,
        azure_deployment=deployment,  # tvůj deployment name
        api_key=UPSTREAM_API_KEY,
        api_version=UPSTREAM_API_VERSION
    )

    azureCompletions: AsyncCompletions = client.chat.completions
    resp = await azureCompletions.create(
            model=deployment,          # = deployment name
            messages=[
                {"role": "system", "content": "You are assistent."},
                {"role": "user", "content": query}
            ],
            temperature=0.8,
            max_tokens=1000,
        )
    asjson = resp.model_dump()
    return asjson

@app.middleware("http")
async def access_log(request: Request, call_next):
    # --- request info ---
    url = str(request.url)                   # plná URL
    path = request.url.path                  # jen /cesta
    query = request.url.query                # bez '?'
    method = request.method
    scheme = request.scope.get("scheme")
    http_ver = request.scope.get("http_version")
    client_host, client_port = (request.client.host, request.client.port) if request.client else (None, None)
    ua = request.headers.get("user-agent", "")
    xff = request.headers.get("x-forwarded-for")
    req_id = request.headers.get("x-request-id")

    print(f"[REQ] {method} {url} hv={http_ver} client={client_host}:{client_port} ua={ua[:80]} xff={xff} req_id={req_id}")

    # --- timing ---
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        dur = (time.perf_counter() - start)
    # --- response info ---
    status = getattr(response, "status_code", None)
    clen = response.headers.get("content-length")
    ctype = response.headers.get("content-type")
    upstream_id = response.headers.get("x-request-id")  # pokud ho upstream přepošleš

    # přidej header s časem
    response.headers["X-Process-Time"] = f"{dur:.6f}"

    print(f"[RES] {method} {path}{'?' + query if query else ''} -> {status} len={clen} type={ctype} t={dur:.3f}s upstream_id={upstream_id}")
    return response

# from gui import init_gui
# init_gui(app)

# from management import router
# app.include_router(router)
if __name__ == "__main__":
    # Pokud chceš TLS přímo v uvicorn:
    # uvicorn.run(app, host=PROXY_BIND, port=PROXY_PORT, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
    uvicorn.run(app, host=PROXY_BIND, port=PROXY_PORT)
