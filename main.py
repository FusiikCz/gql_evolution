import os
import socket
import asyncio
import datetime

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse, FileResponse
from strawberry.fastapi import GraphQLRouter

import logging
import logging.handlers

from sqlalchemy import select, func, text

from src.GraphTypeDefinitions import schema
from src.DBDefinitions import (
    startEngine,
    ComposeConnectionString,
    ApiKeyModel,
    UsageModel,
)
from src.DBFeeder import initDB

# region logging setup

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s.%(msecs)03d\t%(levelname)s:\t%(message)s', 
    datefmt='%Y-%m-%dT%I:%M:%S')
SYSLOGHOST = os.getenv("SYSLOGHOST", None)
if SYSLOGHOST is not None:
    [address, strport, *_] = SYSLOGHOST.split(':')
    assert len(_) == 0, f"SYSLOGHOST {SYSLOGHOST} has unexpected structure, try `localhost:514` or similar (514 is UDP port)"
    port = int(strport)
    my_logger = logging.getLogger()
    my_logger.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address=(address, port), socktype=socket.SOCK_DGRAM)
    #handler = logging.handlers.SocketHandler('10.10.11.11', 611)
    my_logger.addHandler(handler)

# endregion

# region ENV setup and validation
def getEnvWithDefault(name: str, default: str, description: str = ""):
    """
    Get environment variable with a default value.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        description: Optional description for logging
    
    Returns:
        Environment variable value or default
    """
    value = os.getenv(name, default)
    if description:
        logging.info(f"Environment variable {name} = {value} ({description})")
    return value

def getEnvRequired(name: str, description: str = ""):
    """
    Get required environment variable. Raises AssertionError if not set.
    
    Args:
        name: Environment variable name
        description: Optional description for error message
    
    Returns:
        Environment variable value
    
    Raises:
        AssertionError: If environment variable is not set
    """
    value = os.getenv(name, None)
    assert value is not None, f"Required environment variable {name} is not set. {description}"
    if description:
        logging.info(f"Required environment variable {name} = {value}")
    return value

# Environment variables with defaults (optional)
DEMO_STR = getEnvWithDefault("DEMO", "False", "Demo mode flag (True/False)")
GQLUG_ENDPOINT_URL = getEnvWithDefault("GQLUG_ENDPOINT_URL", "", "GQL User Group endpoint URL (optional)")

# Validate DEMO format
assert DEMO_STR.lower() in ("true", "false", "1", "0", "yes", "no"), \
    f"DEMO environment variable must be one of: True/False/1/0/yes/no, got: {DEMO_STR}"
DEMO = DEMO_STR.lower() in ("true", "1", "yes")

# Log environment configuration at startup
logging.info("=" * 60)
logging.info("Environment Configuration:")
logging.info(f"  DEMO = {DEMO} (from '{DEMO_STR}')")
logging.info(f"  GQLUG_ENDPOINT_URL = {GQLUG_ENDPOINT_URL if GQLUG_ENDPOINT_URL else 'Not configured (optional)'}")
logging.info("=" * 60)

if DEMO:
    print("####################################################")
    print("#                                                  #")
    print("# RUNNING IN DEMO                                  #")
    print("#                                                  #")
    print("####################################################")
    logging.info("####################################################")
    logging.info("#                                                  #")
    logging.info("# RUNNING IN DEMO                                  #")
    logging.info("#                                                  #")
    logging.info("####################################################")
else:
    print("####################################################")
    print("#                                                  #")
    print("# RUNNING DEPLOYMENT                               #")
    print("#                                                  #")
    print("####################################################")
    logging.info("####################################################")
    logging.info("#                                                  #")
    logging.info("# RUNNING DEPLOYMENT                               #")
    logging.info("#                                                  #")
    logging.info("####################################################")

# endregion

# region DB setup

## Definice GraphQL typu (pomoci strawberry https://strawberry.rocks/)
## Strawberry zvoleno kvuli moznosti mit federovane GraphQL API (https://strawberry.rocks/docs/guides/federation, https://www.apollographql.com/docs/federation/)
## Definice DB typu (pomoci SQLAlchemy https://www.sqlalchemy.org/)
## SQLAlchemy zvoleno kvuli moznost komunikovat s DB asynchronne
## https://docs.sqlalchemy.org/en/14/core/future.html?highlight=select#sqlalchemy.future.select


## Zabezpecuje prvotni inicializaci DB a definovani Nahodne struktury pro "Univerzity"
# from gql_workflow.DBFeeder import createSystemDataStructureRoleTypes, createSystemDataStructureGroupTypes

connectionString = ComposeConnectionString()

def singleCall(asyncFunc):
    """Dekorator, ktery dovoli, aby dekorovana funkce byla volana (vycislena) jen jednou. Navratova hodnota je zapamatovana a pri dalsich volanich vracena.
    Dekorovana funkce je asynchronni.
    """
    resultCache = {}

    async def result():
        if resultCache.get("result", None) is None:
            resultCache["result"] = await asyncFunc()
        return resultCache["result"]

    return result

@singleCall
async def RunOnceAndReturnSessionMaker():
    """Provadi inicializaci asynchronniho db engine, inicializaci databaze a vraci asynchronni SessionMaker.
    Protoze je dekorovana, volani teto funkce se provede jen jednou a vystup se zapamatuje a vraci se pri dalsich volanich.
    """

    makeDrop = DEMO  # Use globally configured DEMO flag
    logging.info(f'starting engine for "{connectionString} makeDrop={makeDrop}"')

    result = await startEngine(
        connectionstring=connectionString, makeDrop=makeDrop, makeUp=True
    )   
    assert result is not None, "Unable to start engine"
    ###########################################################################################################################
    #
    # zde definujte do funkce asyncio.gather
    # vlozte asynchronni funkce, ktere maji data uvest do prvotniho konzistentniho stavu
    async def initDBAndReport():
        logging.info(f"initializing system structures")
        await initDB(result)
        logging.info(f"all done")
        print(f"all done")

    # asyncio.create_task(coro=initDBAndReport())
    await initDBAndReport()

    #
    #
    ###########################################################################################################################
    
    return result

# endregion

# region FastAPI setup
async def get_context(request: Request):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
    result = {
        "request": request,
        "asyncSessionMaker": asyncSessionMaker
    }
    
    # Note: Loaders are automatically initialized by SessionCommitExtensionFactory
    # using the loaders_factory parameter. No need to create them here manually.
    # The extension creates a session and loaders for each GraphQL request lifecycle.
    
    # DEV/DEMO ONLY:
    # In DEMO mode we inject a test user so mutations can be demonstrated without full auth.
    # In production (DEMO=False) DO NOT inject any user/roles — this would bypass authentication.
    # Note: DEMO is set globally from environment variable at module load time
    if DEMO:
        user_roles = [
            {"roletype": {"name": "administrátor"}},
            {"roletype": {"name": "api_key_administrator"}},
        ]
        user = {
            "id": "d3e6c9d5-afff-4e7e-896a-257271bed4a1",
            "name": "Jan Novák",
            "email": "jan.novak@example.com",
            "roles": user_roles,
        }
        result["user"] = user
        result["user_roles"] = user_roles
    
    return result

innerlifespan = None
@asynccontextmanager
async def dummy(app: FastAPI):
    yield 

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.DBFeeder import backupDB
    icm = dummy if innerlifespan is None else innerlifespan
    async with icm(app):
        print(f"FastAPI.lifespan {innerlifespan is None}")
        initizalizedEngine = await RunOnceAndReturnSessionMaker()
        try:
            yield
        finally:
            pass
        await backupDB(initizalizedEngine)
    
    # print("App shutdown, nothing to do")

app = FastAPI(lifespan=lifespan)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)

from uoishelpers.schema import SessionCommitExtensionFactory
from src.Dataloaders import createLoadersContext
schema.extensions.append(
    SessionCommitExtensionFactory(session_maker_factory=RunOnceAndReturnSessionMaker, loaders_factory=createLoadersContext)
)


app.include_router(graphql_app, prefix="/gql")

@app.get("/voyager", response_class=FileResponse)
async def graphiql():
    realpath = os.path.realpath("./src/Htmls/voyager.html")
    return realpath

@app.get("/doc", response_class=FileResponse)
async def graphiql():
    realpath = os.path.realpath("./src/Htmls/liveschema.html")
    return realpath

@app.get("/ui", response_class=FileResponse)
async def graphiql():
    realpath = os.path.realpath("./src/Htmls/livedata.html")
    return realpath

@app.get("/test", response_class=FileResponse)
async def graphiql():
    realpath = os.path.realpath("./src/Htmls/tests.html")
    return realpath

async def _collect_analytics_payload(async_session_maker):
    """Shared analytics aggregation used by multiple endpoints."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with async_session_maker() as session:
        stmt = select(
            func.count(UsageModel.id).label('total_requests'),
            func.coalesce(func.sum(UsageModel.total_tokens), 0).label('total_tokens'),
            func.coalesce(func.sum(UsageModel.cost_usd), 0.0).label('total_cost'),
            func.coalesce(func.avg(UsageModel.total_tokens), 0.0).label('avg_tokens_per_request')
        )

        result = await session.execute(stmt)
        stats = result.first()

        stmt_top = select(
            ApiKeyModel.id,
            ApiKeyModel.name,
            ApiKeyModel.prefix,
            ApiKeyModel.is_active,
            func.coalesce(func.sum(UsageModel.total_tokens), 0).label('total_usage'),
            func.coalesce(func.sum(UsageModel.cost_usd), 0.0).label('total_cost')
        ).outerjoin(
            UsageModel,
            (UsageModel.api_key_id == ApiKeyModel.id) & (UsageModel.ts >= start_of_month)
        ).group_by(
            ApiKeyModel.id
        ).order_by(
            func.coalesce(func.sum(UsageModel.total_tokens), 0).desc()
        ).limit(10)

        result_top = await session.execute(stmt_top)
        top_keys = [
            {
                "id": str(row.id),
                "name": row.name,
                "prefix": row.prefix,
                "is_active": row.is_active,
                "total_usage": int(row.total_usage),
                "total_cost": float(row.total_cost)
            }
            for row in result_top.all()
        ]

    return {
        "period": {
            "start": start_of_month.isoformat(),
            "end": now.isoformat()
        },
        "statistics": {
            "total_requests": int(stats.total_requests) if stats and stats.total_requests is not None else 0,
            "total_tokens": int(stats.total_tokens) if stats and stats.total_tokens is not None else 0,
            "total_cost_usd": float(stats.total_cost) if stats and stats.total_cost is not None else 0.0,
            "avg_tokens_per_request": float(stats.avg_tokens_per_request) if stats and stats.avg_tokens_per_request is not None else 0.0
        },
        "top_api_keys": top_keys
    }

@app.get("/diagnostics")
async def diagnostics(
    request: Request,
    include_analytics: bool = Query(True),
    include_graphql: bool = Query(True)
):
    """
    Comprehensive diagnostics endpoint returning health info and optional snapshots.
    """
    async_session_maker = await RunOnceAndReturnSessionMaker()

    response_payload = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "links": {
            "graphql": str(request.base_url) + "gql",
            "analytics": str(request.base_url) + "analytics",
            "dashboard": str(request.base_url) + "dashboard",
            "voyager": str(request.base_url) + "voyager",
        },
    }

    status = "ok"

    # Database connectivity check
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        response_payload["database"] = {"status": "ok"}
    except Exception as exc:
        status = "degraded"
        response_payload["database"] = {"status": "error", "detail": str(exc)}

    # Analytics snapshot reuse
    if include_analytics and response_payload["database"]["status"] == "ok":
        try:
            response_payload["analytics"] = await _collect_analytics_payload(async_session_maker)
        except Exception as exc:
            status = "degraded"
            response_payload["analytics"] = {"status": "error", "detail": str(exc)}

    # GraphQL smoke test (read-only operations)
    if include_graphql:
        graphql_results = []
        try:
            from httpx import AsyncClient, ASGITransport

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url=str(request.base_url)) as client:
                operations = [
                    ("hello", {"query": "query TestHello { hello }"}),
                    ("myApiKeys", {"query": "query TestMyKeys { myApiKeys { id name isActive } }"}),
                    ("usageStats", {"query": "query TestUsageStats { usageStats { totalRequests totalTokens totalCost averageTokensPerRequest } }"}),
                    ("expiredApiKeys", {"query": "query TestExpired { expiredApiKeys { id name isActive } }"}),
                ]

                for name, payload in operations:
                    try:
                        response = await client.post("/gql", json=payload, timeout=30)
                        content = response.json()
                        graphql_results.append(
                            {
                                "operation": name,
                                "status_code": response.status_code,
                                "errors": content.get("errors"),
                                "has_data": "data" in content
                            }
                        )
                    except Exception as op_exc:
                        status = "degraded"
                        graphql_results.append({"operation": name, "error": str(op_exc)})
        except Exception as exc:
            status = "degraded"
            graphql_results.append({"operation": "internal", "error": str(exc)})

        response_payload["graphql_checks"] = graphql_results

    response_payload["status"] = status

    return JSONResponse(response_payload)

@app.get("/dashboard", response_class=FileResponse)
async def analytics_dashboard():
    realpath = os.path.realpath("./src/Htmls/analytics.html")
    return realpath

import prometheus_client
@app.get("/metrics")
async def metrics():
    return Response(
        content=prometheus_client.generate_latest(), 
        media_type=prometheus_client.CONTENT_TYPE_LATEST
        )

@app.get("/analytics")
async def analytics():
    """
    Analytics endpoint - returns usage statistics and top API keys
    """
    async_session_maker = await RunOnceAndReturnSessionMaker()
    payload = await _collect_analytics_payload(async_session_maker)
    return JSONResponse(payload)


logging.info("All initialization is done")

# @app.get('/hello')
# def hello():
#    return {'hello': 'world'}

###########################################################################################################################
#
# pokud jste pripraveni testovat GQL funkcionalitu, rozsirte apollo/server.js
#
###########################################################################################################################
# endregion


# region nicegui
from main_nicegui import nicegui, nicegui_app
nicegui.ui.run_with(
    app,
    title="GQL Evolution",
    mount_path="/nicegui",
    favicon="🚀",
    dark=None,
    tailwind=True,
    storage_secret="SUPER-SECRET")
# endregion

# region mcp
from fastmcp import Client
from main_mcp import mcp_app, mcp_app_sse
innerlifespan = mcp_app.lifespan

app.mount(path="/mcp", app=mcp_app_sse)
app.mount(path="/mcp_no_sse", app=mcp_app)


@app.get("/testmcp")
async def test_mcp() -> dict:
    """Test MCP functionality - returns info about MCP server."""
    from main_mcp import mcp
    
    result = {
        "status": "ok",
        "mcp_name": mcp.name,
        "endpoints": {
            "mcp_sse": "/mcp",
            "mcp_http": "/mcp_no_sse"
        },
        "info": "MCP server is running. Use an MCP client (like Dive) to connect."
    }
    
    # Try to get registered tools info
    try:
        # FastMCP stores tools in _tool_manager
        if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, '_tools'):
            result["available_tools"] = list(mcp._tool_manager._tools.keys())
        elif hasattr(mcp, 'tools'):
            result["available_tools"] = list(mcp.tools.keys()) if isinstance(mcp.tools, dict) else [str(t) for t in mcp.tools]
    except Exception as e:
        result["tools_error"] = str(e)
    
    return result
# endregion


@app.middleware("http")
async def add_process_log(request: Request, call_next):
    print(f"http.middleware base_url={request.base_url}")
    response = await call_next(request)
    return response

@mcp_app.middleware("http")
async def add_process_log(request: Request, call_next):
    print(f"mcp.http.middleware base_url={request.base_url}")
    try:
        response = await call_next(request)
    except Exception as e:
        print("chyba {e}")
        raise e
    return response
# v následujícím dotazu identifikuj datové entity, a podmínky, které mají splňovat. seznam datových entit (jejich odhadnuté názvy) uveď jako json list obsahující stringy - názvy seznam podmínek uveď jako json list obsahující dict např. {"name": {"_eq": "Pavel"}} pokud se jedná o podmínku v relaci, odpovídající dict je tento {"related_entity": {"attribute_name": {"_eq": "value"}}} v dict nikdy není použit klíč, který by sdružoval více názvů atributů dotaz: najdi mi všechny uživatele, kteří jsou členy katedry K209