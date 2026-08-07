# Story 6-4: Expose cross-store queries through Hasura GraphQL

Status: done

Baseline commit: 289a93e

## Story

As a Platform User,
I want a unified GraphQL API via Hasura at `/gql`,
so that I can run cross-store queries combining CouchDB entity state, YugabyteDB resources, and ClickHouse telemetry under a role-based permission model.

## Acceptance Criteria

1. Given a GraphQL query, when it joins CouchDB entities with YugabyteDB resources, then it resolves in under 2 seconds.
2. Given a GraphQL query, when it references ClickHouse telemetry, then it is federated with entity and resource data.
3. Given a user role, when a query is issued, then Hasura enforces the role-based permission model.
4. Given a request, when routed, then the endpoint is exposed at `/gql`.
5. Given a schema, when deployed, then cross-store join configuration is declared for couchdb_entities, yugabytedb_resources, and clickhouse_telemetry.

## Implementation Plan

- Add `HasuraGraphQL` binding to the platform contract under `gitops/entity-store/base/`.
- Declare the GraphQL gateway Deployment/Service, join config, and permission model.
- Implement `graphql-gateway.py` CLI that validates cross-store queries against the join config and enforces role-based permissions.
- Add step wrapper and validation test.

## Files

- `gitops/entity-store/base/graphql-gateway.yaml` (new)
- `scripts/graphql-gateway.py` (new)
- `scripts/steps/34-graphql-gateway.py` (new)
- `tests/test_graphql_gateway.py` (new)
