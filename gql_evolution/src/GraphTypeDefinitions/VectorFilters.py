"""
Vector filter types for semantic similarity search on embedding vectors.

These filters enable AI-powered search using vector embeddings stored in the database.
Compatible with pgvector extension for PostgreSQL.
"""

import typing
import strawberry


@strawberry.input(
    description="""Vector similarity filter for cosine similarity search.
    Finds entities with embeddings similar to the provided vector.
    Higher threshold values (closer to 1.0) return more similar results.
    Threshold range: 0.0 (dissimilar) to 1.0 (identical).
    """
)
class VectorSimilarityFilter:
    vector: typing.List[float] = strawberry.field(
        description="""Embedding vector to compare against. Must match the dimension of stored embeddings.
        Example: [0.1, 0.2, 0.3, ..., 0.9] for a 768-dimensional embedding."""
    )
    threshold: float = strawberry.field(
        default=0.8,
        description="""Minimum similarity threshold (0.0-1.0). Default: 0.8.
        Higher values (0.9-1.0) return only very similar results.
        Lower values (0.5-0.8) return more diverse but less similar results."""
    )


@strawberry.input(
    description="""Vector distance filter for Euclidean/L2 distance search.
    Finds entities with embeddings within a specified distance from the provided vector.
    Lower distance values return closer/similar results.
    """
)
class VectorDistanceFilter:
    vector: typing.List[float] = strawberry.field(
        description="""Embedding vector to compare against. Must match the dimension of stored embeddings."""
    )
    max_distance: float = strawberry.field(
        description="""Maximum allowed distance. Lower values return closer results.
        Typical values depend on embedding dimension and normalization."""
    )


@strawberry.input(
    description="""Vector filter operators for semantic similarity search on embedding attributes.
    
    This filter enables AI-powered search using vector embeddings.
    Use _similarity for cosine similarity search (recommended for normalized embeddings).
    Use _distance for Euclidean distance search.
    
    Example usage:
    {
      "embedding": {
        "_similarity": {
          "vector": [0.1, 0.2, 0.3, ...],
          "threshold": 0.8
        }
      }
    }
    
    Or with distance:
    {
      "embedding": {
        "_distance": {
          "vector": [0.1, 0.2, 0.3, ...],
          "max_distance": 0.5
        }
      }
    }
    
    Note: The vector dimension must match the dimension of stored embeddings (typically 768 or 1536).
    """
)
class VectorFilter:
    _similarity: typing.Optional[VectorSimilarityFilter] = strawberry.field(
        default=None,
        description="""Find entities with embeddings similar to the given vector using cosine similarity.
        Recommended for normalized embeddings. Returns entities where similarity >= threshold.
        Example: {"_similarity": {"vector": [...], "threshold": 0.8}}"""
    )
    
    _distance: typing.Optional[VectorDistanceFilter] = strawberry.field(
        default=None,
        description="""Find entities with embeddings within the specified distance using Euclidean distance.
        Returns entities where distance <= max_distance.
        Example: {"_distance": {"vector": [...], "max_distance": 0.5}}"""
    )

