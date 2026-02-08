"""
Tests for computed fields in EventGQLModel.

Tests:
- valid_ field (checks if event is currently valid based on startdate/enddate)
- duration field (calculates event duration in different time units)
"""
import pytest
import logging
import datetime
from src.GraphTypeDefinitions import schema
from src.GraphTypeDefinitions.TimeUnit import TimeUnit
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)
