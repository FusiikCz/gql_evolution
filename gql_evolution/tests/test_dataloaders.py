import pytest
import logging

from .shared import (
    createInfo,
    prepare_in_memory_sqllite
    )

from uoishelpers.resolvers import getUserFromInfo

@pytest.mark.asyncio
async def test_get_user():
    #asyncSessionMaker = await prepare_in_memory_sqllite()
    info = createInfo(asyncSessionMaker=None, withuser=True)

    user = getUserFromInfo(info)
    logging.info(user)
    assert user is not None
    #assert False