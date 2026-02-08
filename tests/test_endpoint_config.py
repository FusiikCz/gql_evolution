"""
Unit tests for EndpointConfig GraphQL model.
Tests CRUD operations for EndpointConfig entity.
"""
import pytest
import logging
import json
from src.GraphTypeDefinitions import schema
from src.Utils.error_codes import get_error_code
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)

def runAssert(expression, comment):
    """Helper function for assertions in lambda functions"""
    assert expression, comment
