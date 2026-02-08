"""
GraphQL client utilities for authenticated API access.

This module provides functions for creating authenticated GraphQL clients
that handle OAuth token management and automatic re-authentication.
"""

async def createGQLClient(*, url: str = "http://localhost:33001/api/gql", username: str, password: str):
    """
    Create an authenticated GraphQL client with automatic token management.
    
    This function:
    1. Authenticates with the OAuth endpoint to obtain a token
    2. Returns a client function that automatically handles token refresh
       when authentication expires
    
    Args:
        url: GraphQL endpoint URL (default: http://localhost:33001/api/gql)
        username: Username for authentication
        password: Password for authentication
    
    Returns:
        Async function that accepts (query, variables, cookies) and returns
        the GraphQL response. The function automatically handles:
        - Token refresh on authentication errors
        - Retry logic for transient failures
        - Proper error handling
    
    Example:
        ```python
        client = await createGQLClient(
            url="http://api.example.com/gql",
            username="user",
            password="pass"
        )
        result = await client(
            "query { user { id name } }",
            variables={}
        )
        ```
    
    Raises:
        Exception: If max re-authentication attempts are reached
    """
    import aiohttp
    async def getToken():
        authurl = url.replace("/api/gql", "/oauth/login3")
        async with aiohttp.ClientSession() as session:
            # print(headers, cookies)
            async with session.get(authurl) as resp:
                json = await resp.json()

            payload = {
                **json,
                "username": username,
                "password": password
            }
            async with session.post(authurl, json=payload) as resp:
                json = await resp.json()
            # print(f"createGQLClient: {json}")
            token = json["token"]
        return token
    token = await getToken()
    total_attempts = 10
    async def client(query, variables, cookies={"authorization": token}):
        # gqlurl = "http://host.docker.internal:33001/api/gql"
        # gqlurl = "http://localhost:33001/api/gql"
        nonlocal total_attempts
        if total_attempts < 1:
            raise Exception(msg="Max attempts to reauthenticate to graphql endpoint has been reached")
        attempts = 2
        while attempts > 0:
            
            payload = {"query": query, "variables": variables}
            # print("Query payload", payload, flush=True)
            try:
                async with aiohttp.ClientSession() as session:
                    # print(headers, cookies)
                    async with session.post(url, json=payload, cookies=cookies) as resp:
                        # print(resp.status)
                        if resp.status != 200:
                            text = await resp.text()
                            # print(text, flush=True)
                            raise Exception(f"Unexpected GQL response", text)
                        else:
                            text = await resp.text()
                            # print(text, flush=True)
                            response = await resp.json()
                            # print(response, flush=True)
                            return response
            except aiohttp.ContentTypeError as e:
                attempts = attempts - 1
                total_attempts = total_attempts - 1
                print(f"attempts {attempts}-{total_attempts}", flush=True)
                nonlocal token
                token = await getToken()

    return client