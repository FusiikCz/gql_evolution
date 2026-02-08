#!/bin/bash
# Script to generate supergraph.graphql using rover CLI in Docker
# This works on Windows, Linux, and macOS

set -e

echo "Generating supergraph schema..."

# Wait for GraphQL endpoint to be available
echo "Waiting for GraphQL endpoint at http://gql_app:8000/gql..."
for i in {1..30}; do
  # Try POST request with simple query (GraphQL endpoints need POST)
  if curl -f -s -X POST http://gql_app:8000/gql \
    -H "Content-Type: application/json" \
    -d '{"query":"{ __typename }"}' > /dev/null 2>&1; then
    echo "GraphQL endpoint is available!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "Error: GraphQL endpoint not available after 30 attempts"
    exit 1
  fi
  sleep 2
done

# Generate supergraph schema using rover CLI
echo "Composing supergraph schema..."
# Use rover from PATH (should be in /root/.rover/bin)
rover supergraph compose \
  --config /config/supergraph.yaml \
  --elv2-license accept \
  > /config/supergraph.graphql

if [ $? -eq 0 ]; then
  echo "Supergraph schema generated successfully!"
  echo "File: /config/supergraph.graphql"
else
  echo "Error generating supergraph schema"
  exit 1
fi
