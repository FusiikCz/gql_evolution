def createGQLClient():

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src import DBDefinitions

    def ComposeCString():
        return "sqlite+aiosqlite:///:memory:"
    
    DBDefinitions.ComposeConnectionString = ComposeCString

    import main
    from uoishelpers.schema import SessionCommitExtension, SessionCommitExtensionFactory
    from src.GraphTypeDefinitions import schema

    if not any(isinstance(ext, SessionCommitExtension) for ext in schema.extensions):
        schema.extensions.append(
            SessionCommitExtensionFactory(
                session_maker_factory=main.RunOnceAndReturnSessionMaker,
                loaders_factory=main.createLoadersContext
            )
        )
    
    client = TestClient(main.app, raise_server_exceptions=False)
    return client

