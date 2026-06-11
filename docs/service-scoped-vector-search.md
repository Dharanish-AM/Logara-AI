# Service-scoped Vector Search

Logara AI stores each vectorized log with a `service_id` payload field in Qdrant.

This prevents semantic search results from mixing logs across unrelated services.

## Ingestion

Structured logs should include a `service_id` field.

Example:

    {
      "service_id": "payments-api",
      "environment": "production",
      "level": "ERROR",
      "message": "database timeout during checkout"
    }

The ingestion layer also supports the older `service` field and maps it into `service_id`.

## Qdrant Payload

Each vectorized log stores payload metadata like:

    {
      "service_id": "payments-api",
      "level": "ERROR",
      "message": "database timeout during checkout",
      "environment": "production"
    }

## Search

Semantic search requires a `service_id` filter.

Example:

    GET /search?query=database timeout&service_id=payments-api

Only Qdrant points matching the requested `service_id` are searched and returned.

Optional filters:

    GET /search?query=timeout&service_id=payments-api&environment=production&severity=ERROR

## Safety

If `service_id` is invalid, the API rejects the request.

If a legacy raw log has no detectable service identifier, the worker stores it under:

    unknown_service
