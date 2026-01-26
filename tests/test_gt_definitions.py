import logging
import sqlalchemy
import sys
import asyncio

import pytest

from src.GraphTypeDefinitions import schema

from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)

def createByIdTest(tableName, queryEndpoint, attributeNames=["id", "name"]):
    @pytest.mark.asyncio
    async def result_test():
        async_session_maker = await prepare_in_memory_sqllite()
        await prepare_demodata(async_session_maker)

        data = get_demodata()
        datarow = data[tableName][0]
        content = "{" + ", ".join(attributeNames) + "}"
        query = "query($id: UUID!){" f"{queryEndpoint}(id: $id)" f"{content}" "}"

        context_value = createContext(async_session_maker)
        variable_values = {"id": f'{datarow["id"]}'}
        
        logging.debug(f"query for {query} with {variable_values}")

        resp = await schema.execute(
            query, context_value=context_value, variable_values=variable_values
        )

        respdata = resp.data[queryEndpoint]

        assert resp.errors is None

        for att in attributeNames:
            assert respdata[att] == f'{datarow[att]}'

    return result_test


def createPageTest(tableName, queryEndpoint, attributeNames=["id", "name"]):
    @pytest.mark.asyncio
    async def result_test():
        async_session_maker = await prepare_in_memory_sqllite()
        await prepare_demodata(async_session_maker)

        data = get_demodata()

        content = "{" + ", ".join(attributeNames) + "}"
        query = "query{" f"{queryEndpoint}" f"{content}" "}"

        context_value = createContext(async_session_maker)
        logging.debug(f"query for {query}")

        resp = await schema.execute(query, context_value=context_value)

        respdata = resp.data[queryEndpoint]
        datarows = data[tableName]

        assert resp.errors is None

        for rowa, rowb in zip(respdata, datarows):
            for att in attributeNames:
                assert rowa[att] == f'{rowb[att]}'

    return result_test

def createResolveReferenceTest(tableName, gqltype, attributeNames=["id", "name"]):
    @pytest.mark.asyncio
    async def result_test():
        async_session_maker = await prepare_in_memory_sqllite()
        await prepare_demodata(async_session_maker)

        data = get_demodata()

        data = get_demodata()
        table = data[tableName]
        for row in table:
            rowid = f"{row['id']}"

            query = (
                'query { _entities(representations: [{ __typename: '+ f'"{gqltype}", id: "{rowid}"' + 
                ' }])' +
                '{' +
                f'...on {gqltype}' + 
                '{ id }'+
                '}' + 
                '}')

            context_value = createContext(async_session_maker)
            logging.debug(f"query for {query}")
            resp = await schema.execute(query, context_value=context_value)
            data = resp.data
            logging.debug(data)
            data = data['_entities'][0]

            assert data['id'] == rowid

    return result_test

def createFrontendQuery(query="{}", variables={}, asserts=[]):
    @pytest.mark.asyncio
    async def test_frontend_query():    
        logging.debug("createFrontendQuery")
        async_session_maker = await prepare_in_memory_sqllite()
        await prepare_demodata(async_session_maker)
        context_value = createContext(async_session_maker)
        logging.debug(f"query for {query} with {variables}")
        resp = await schema.execute(
            query=query, 
            variable_values=variables, 
            context_value=context_value
        )

        assert resp.errors is None
        respdata = resp.data
        logging.debug(f"response: {respdata}")
        for a in asserts:
            a(respdata)
    return test_frontend_query

test_query_event_by_id = createByIdTest(
    tableName="events_evolution", queryEndpoint="eventById",
    attributeNames=["id", "name"]
    )

def runAssert(expression, comment):
    assert expression, comment

test_query_event_extended = createFrontendQuery(
    query="""
        mutation {
        result: eventInsert(
            event: {
                id: "bbedf480-3e1d-435c-b994-1a4991e0b87c",
                name: "new event",
                startDate: "2024-10-10T08:00:00",
                endDate: "2024-10-10T10:00:00"
            }
        ) {
            ... on EventGQLModel {
                id
                name
                lastchange
                startdate
                enddate
                masterevent {
                    id
                }
            }
            ... on InsertError {
                msg
                failed
                code
            }
        }
        }""",
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(data["result"].get("msg", None) is None, "expected insert success"),
        lambda data: runAssert(data["result"].get("startdate", None) is not None, "expected data.result.startdate"),
        lambda data: runAssert(data["result"].get("enddate", None) is not None, "expected data.result.enddate"),
        lambda data: runAssert(data["result"].get("masterevent", None) is None, "expected missing data.result.masterevent")
    ]
)

test_query_event_missing = createFrontendQuery(
    query="""
        query($id: UUID!) {
            result: eventById(id: $id) {
                id
            }
        }""",
    variables={
        "id": "bbedf480-3e1d-435c-b994-eeeeeeeeeeee"
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is None, "expected empty data.result")
    ]
)

test_query_event_with_master = createFrontendQuery(
    query="""
        query($id: UUID!) {
            result: eventById(id: $id) {
                id
                masterevent {
                    id
                }
            }
        }""",
    variables={
        "id": "08ff1c5d-9891-41f6-a824-fc6272adc189"
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(data["result"].get("masterevent", None) is not None, "expected data.result.masterevent")
    ]
)

test_query_event_with_subevents = createFrontendQuery(
    query="""
        query($id: UUID!) {
            result: eventById(id: $id) {
                id
                subevents {
                    id
                }
            }
        }""",
    variables={
        "id": "5194663f-11aa-4775-91ed-5f3d79269fed"
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(len(data["result"].get("subevents", [])) > 0, "expected data.result.subevents")
    ]
)

@pytest.mark.asyncio
async def test_event_update():    
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    query="""
        query($id: UUID!) {
            result: eventById(id: $id) {
                id
                lastchange
            }
        }"""
    variables={
        "id": "5194663f-11aa-4775-91ed-5f3d79269fed"
    }
    logging.debug(f"query for {query} with {variables}")
    resp = await schema.execute(
        query=query, 
        variable_values=variables, 
        context_value=context_value
    )

    assert resp.errors is None
    
    respdata = resp.data
    lastchange = respdata["result"]["lastchange"]

    query="""
        mutation(
            $id: UUID!,
            $lastchange: DateTime!,
            $name: String!
        ) {
        result: eventUpdate(
            event: {
            id: $id, 
            name: $name,
            lastchange: $lastchange
            }
        ) {
            ... on EventGQLModel {
                id
                name
                lastchange
            }
            ... on EventGQLModelUpdateError {
                msg
                failed
            }
        }
        }"""
    newName = "nameX"
    variables={
        "id": "5194663f-11aa-4775-91ed-5f3d79269fed",
        "lastchange": lastchange,
        "name": newName
    }
    logging.debug(f"query for {query} with {variables}")
    resp = await schema.execute(
        query=query, 
        variable_values=variables, 
        context_value=context_value
    )

    assert resp.errors is None
    respdata = resp.data
    assert respdata is not None
    result = respdata.get("result", None)
    assert result is not None
    assert "msg" not in result
    name = result.get("name", None)
    assert name is not None
    assert name == newName

test_query_event_failed_update = createFrontendQuery(
    query="""
        mutation(
            $id: UUID!,
            $lastchange: DateTime!,
            $name: String!
        ) {
        result: eventUpdate(
            event: {
            id: $id, 
            name: $name,
            lastchange: $lastchange
            }
        ) {
            ... on EventGQLModel {
                id
                name
                lastchange
            }
            ... on EventGQLModelUpdateError {
                msg
                failed
            }
        }
        }""",
    variables={
        "id": "5194663f-11aa-4775-91ed-5f3d79269fed",
        "name": "nameX",
        "lastchange": "2023-10-29T11:00:00"
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(data["result"].get("msg", None) is not None, "expected update error")
    ]
)

test_query_event_sensitive_failed = createFrontendQuery(
    query="""
        query($id: UUID!) {
            result: eventById(id: $id) {
                id
                name
                lastchange
                name
            }
        }""",
    variables={
        "id": "5194663f-11aa-4775-91ed-5f3d79269fed",
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(data["result"].get("name", None) is not None, "expected not None ")
    ]
)

test_query_hello = createFrontendQuery(
    query="""{ hello }""",
    variables={},
    asserts = [
        lambda data: runAssert(data.get("hello", None) is not None, "expected data.hello"),
    ]
)

test_query_event_with_users = createFrontendQuery(
    query="""
        query($id: UUID!) {
            result: eventById(id: $id) {
                id
                name
                lastchange
                userInvitations { 
                    user {
                        id
                        name
                    }
                }
            }
        }""",
    variables={
        "id": "45b2df80-ae0f-11ed-9bd8-0242ac110002",
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(data["result"].get("userInvitations", None) is not None, "expected not None ")
    ]
)

test_query_user_with_events = createFrontendQuery(
    query="""
        query($id: UUID!) { 
            result: eventInvitationPage(where: { user_id: { _eq: $id } }) {
                id
                event {
                    id
                    name
                }
            }
        }""",
    variables={
        "id": "d3e6c9d5-afff-4e7e-896a-257271bed4a1",
    },
    asserts = [
        lambda data: runAssert(data.get("result", None) is not None, "expected data.result"),
        lambda data: runAssert(len(data.get("result", [])) > 0, "expected at least one invitation")
    ]
)