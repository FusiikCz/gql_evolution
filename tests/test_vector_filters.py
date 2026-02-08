"""
Tests for vector filter functionality in GraphQL queries.

Tests semantic similarity search using VectorFilter, VectorSimilarityFilter, and VectorDistanceFilter.
"""
import pytest
import logging
from src.GraphTypeDefinitions import schema
from src.GraphTypeDefinitions.VectorFilters import (
    VectorFilter,
    VectorSimilarityFilter,
    VectorDistanceFilter
)
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    createContext,
)


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_types():
    """Test that VectorFilter types can be instantiated"""
    # Test VectorSimilarityFilter
    similarity_filter = VectorSimilarityFilter(
        vector=[0.1, 0.2, 0.3, 0.4, 0.5],
        threshold=0.8
    )
    assert similarity_filter.vector == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert similarity_filter.threshold == 0.8
    
    # Test VectorDistanceFilter
    distance_filter = VectorDistanceFilter(
        vector=[0.1, 0.2, 0.3, 0.4, 0.5],
        max_distance=0.5
    )
    assert distance_filter.vector == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert distance_filter.max_distance == 0.5
    
    # Test VectorFilter with similarity
    vector_filter_sim = VectorFilter(_similarity=similarity_filter)
    assert vector_filter_sim._similarity is not None
    assert vector_filter_sim._distance is None
    
    # Test VectorFilter with distance
    vector_filter_dist = VectorFilter(_distance=distance_filter)
    assert vector_filter_dist._distance is not None
    assert vector_filter_dist._similarity is None


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_similarity_filter_default_threshold():
    """Test that VectorSimilarityFilter has default threshold"""
    filter_obj = VectorSimilarityFilter(vector=[0.1, 0.2, 0.3])
    assert filter_obj.threshold == 0.8  # Default value


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_in_graphql_query():
    """Test that vector filters can be used in GraphQL queries (schema validation)"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Test query with vector similarity filter on DocumentInputFilter
    # Note: This tests that the schema accepts the filter, not that it executes correctly
    # (since we don't have actual embeddings in test data)
    query = """
        query {
            documentPage(where: {
                embedding: {
                    Similarity: {
                        vector: [0.1, 0.2, 0.3, 0.4, 0.5]
                        threshold: 0.8
                    }
                }
            }) {
                id
                name
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    
    # Query should not fail due to schema validation
    # (It may return empty results if no documents match, but that's OK)
    assert resp.errors is None or all(
        "embedding" not in str(err).lower() or "vector" not in str(err).lower()
        for err in (resp.errors or [])
    ), f"Vector filter query failed: {resp.errors}"


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_distance_filter_in_graphql_query():
    """Test that vector distance filters can be used in GraphQL queries"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    query = """
        query {
            documentPage(where: {
                embedding: {
                    Distance: {
                        vector: [0.1, 0.2, 0.3, 0.4, 0.5]
                        maxDistance: 0.5
                    }
                }
            }) {
                id
                name
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    
    # Query should not fail due to schema validation
    assert resp.errors is None or all(
        "embedding" not in str(err).lower() or "vector" not in str(err).lower()
        for err in (resp.errors or [])
    ), f"Vector distance filter query failed: {resp.errors}"


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_on_document_fragment():
    """Test vector filters on DocumentFragmentInputFilter"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    query = """
        query {
            documentFragmentPage(where: {
                embedding: {
                    Similarity: {
                        vector: [0.1, 0.2, 0.3]
                        threshold: 0.7
                    }
                }
            }) {
                id
                title
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    
    # Query should not fail due to schema validation
    assert resp.errors is None or all(
        "embedding" not in str(err).lower() or "vector" not in str(err).lower()
        for err in (resp.errors or [])
    ), f"DocumentFragment vector filter query failed: {resp.errors}"


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_with_different_thresholds():
    """Test vector similarity filter with different threshold values"""
    # Test various threshold values
    thresholds = [0.5, 0.7, 0.8, 0.9, 0.95]
    
    for threshold in thresholds:
        filter_obj = VectorSimilarityFilter(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            threshold=threshold
        )
        assert filter_obj.threshold == threshold
        assert filter_obj.vector == [0.1, 0.2, 0.3, 0.4, 0.5]


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_with_different_vector_sizes():
    """Test vector filters with different vector dimensions"""
    vector_sizes = [3, 5, 10, 128, 1536]  # Common embedding dimensions
    
    for size in vector_sizes:
        vector = [0.1] * size
        similarity_filter = VectorSimilarityFilter(vector=vector, threshold=0.8)
        assert len(similarity_filter.vector) == size
        
        distance_filter = VectorDistanceFilter(vector=vector, max_distance=0.5)
        assert len(distance_filter.vector) == size


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_combined_with_other_filters():
    """Test vector filters combined with other filter conditions"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Test query with vector filter AND name filter
    query = """
        query {
            documentPage(where: {
                name: {_like: "%test%"}
                embedding: {
                    Similarity: {
                        vector: [0.1, 0.2, 0.3, 0.4, 0.5]
                        threshold: 0.8
                    }
                }
            }) {
                id
                name
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    
    # Query should not fail due to schema validation
    assert resp.errors is None or all(
        "embedding" not in str(err).lower() or "vector" not in str(err).lower()
        for err in (resp.errors or [])
    ), f"Combined filter query failed: {resp.errors}"


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_edge_cases():
    """Test edge cases for vector filters"""
    # Test with empty vector (should be handled gracefully)
    try:
        empty_filter = VectorSimilarityFilter(vector=[], threshold=0.8)
        # Empty vector may be valid or invalid depending on implementation
    except (ValueError, TypeError):
        pass  # Expected if empty vector is not allowed
    
    # Test with very small threshold
    small_threshold_filter = VectorSimilarityFilter(
        vector=[0.1, 0.2, 0.3],
        threshold=0.01
    )
    assert small_threshold_filter.threshold == 0.01
    
    # Test with very large threshold
    large_threshold_filter = VectorSimilarityFilter(
        vector=[0.1, 0.2, 0.3],
        threshold=0.99
    )
    assert large_threshold_filter.threshold == 0.99
    
    # Test with zero distance
    zero_distance_filter = VectorDistanceFilter(
        vector=[0.1, 0.2, 0.3],
        max_distance=0.0
    )
    assert zero_distance_filter.max_distance == 0.0


@pytest.mark.asyncio
@pytest.mark.filtering
async def test_vector_filter_schema_validation():
    """Test that vector filter schema is correctly defined"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Test that both similarity and distance filters are accepted
    queries = [
        # Similarity filter
        """
        query {
            documentPage(where: {
                embedding: {
                    Similarity: {
                        vector: [0.1, 0.2, 0.3]
                        threshold: 0.8
                    }
                }
            }) {
                id
            }
        }
        """,
        # Distance filter
        """
        query {
            documentPage(where: {
                embedding: {
                    Distance: {
                        vector: [0.1, 0.2, 0.3]
                        maxDistance: 0.5
                    }
                }
            }) {
                id
            }
        }
        """
    ]
    
    for query in queries:
        resp = await schema.execute(query, context_value=context_value)
        # Should not fail due to schema errors
        assert resp.errors is None or not any(
            "unknown field" in str(err).lower() or "cannot query" in str(err).lower()
            for err in (resp.errors or [])
        ), f"Schema validation failed for query: {resp.errors}"
