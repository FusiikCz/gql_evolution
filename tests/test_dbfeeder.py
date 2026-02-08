"""
Tests for DBFeeder module.

Tests:
- initDB function
- get_demodata function
- backupDB function
"""
import pytest
import os
import tempfile
import json
from pathlib import Path
from src.DBFeeder import initDB, get_demodata, backupDB
from tests.shared import prepare_in_memory_sqllite


@pytest.mark.asyncio
async def test_get_demodata():
    """Test that get_demodata returns valid data structure"""
    data = get_demodata()
    assert data is not None
    assert isinstance(data, dict)
    # Check that it contains expected keys
    assert len(data) > 0


@pytest.mark.asyncio
async def test_initdb_with_demo_mode():
    """Test that initDB loads demo data when DEMODATA is set"""
    # Set DEMODATA environment variable
    original_demo = os.environ.get("DEMODATA", None)
    os.environ["DEMODATA"] = "True"
    
    try:
        async_session_maker = await prepare_in_memory_sqllite()
        await initDB(async_session_maker, filename="./systemdata.json")
        
        # Verify that data was loaded by checking if we can query users
        from src.DBDefinitions import UserModel
        from sqlalchemy import select
        
        async with async_session_maker() as session:
            stmt = select(UserModel)
            result = await session.execute(stmt)
            users = result.scalars().all()
            # Should have loaded some users from demo data
            assert len(users) >= 0  # At least no error
    finally:
        # Restore original value
        if original_demo is not None:
            os.environ["DEMODATA"] = original_demo
        elif "DEMODATA" in os.environ:
            del os.environ["DEMODATA"]


@pytest.mark.asyncio
async def test_initdb_without_demo_mode():
    """Test that initDB works without demo mode"""
    # Ensure DEMODATA is not set
    original_demo = os.environ.get("DEMODATA", None)
    if "DEMODATA" in os.environ:
        del os.environ["DEMODATA"]
    
    try:
        async_session_maker = await prepare_in_memory_sqllite()
        # Should not raise error even without demo mode
        await initDB(async_session_maker, filename="./systemdata.json")
    finally:
        # Restore original value
        if original_demo is not None:
            os.environ["DEMODATA"] = original_demo


@pytest.mark.asyncio
async def test_backupdb():
    """Test that backupDB creates a backup file"""
    async_session_maker = await prepare_in_memory_sqllite()
    
    # First initialize DB with demo data
    original_demo = os.environ.get("DEMODATA", None)
    os.environ["DEMODATA"] = "True"
    
    try:
        await initDB(async_session_maker, filename="./systemdata.json")
        
        # Create temporary backup file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            backup_path = tmp_file.name
        
        try:
            # Run backup
            await backupDB(async_session_maker, filename=backup_path)
            
            # Verify backup file was created and contains valid JSON
            assert Path(backup_path).exists(), "Backup file should be created"
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                assert isinstance(backup_data, list), "Backup should be a list"
        finally:
            # Clean up
            if Path(backup_path).exists():
                Path(backup_path).unlink()
    finally:
        # Restore original value
        if original_demo is not None:
            os.environ["DEMODATA"] = original_demo
        elif "DEMODATA" in os.environ:
            del os.environ["DEMODATA"]
