COMPLEX_OTEL_PAYLOAD = {
    "resourceLogs": [
        {
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "complex-service"}},
                    {"key": "host.name", "value": {"stringValue": "server-1"}},
                    {
                        "key": "cloud.provider",
                        "value": {"stringValue": "aws"}
                    }
                ]
            },
            "scopeLogs": [
                {
                    "scope": {
                        "name": "my.library",
                        "version": "1.0.0"
                    },
                    "logRecords": [
                        {
                            "timeUnixNano": "1682124012000000000",
                            "severityNumber": 17,
                            "severityText": "ERROR",
                            "body": {
                                "stringValue": "Complex error occurred"
                            },
                            "attributes": [
                                {
                                    "key": "http.request.headers",
                                    "value": {
                                        "kvlistValue": {
                                            "values": [
                                                {"key": "user-agent", "value": {"stringValue": "Mozilla/5.0"}},
                                                {"key": "content-type", "value": {"stringValue": "application/json"}}
                                            ]
                                        }
                                    }
                                },
                                {
                                    "key": "db.query.params",
                                    "value": {
                                        "arrayValue": {
                                            "values": [
                                                {"stringValue": "user_id_123"},
                                                {"intValue": "42"}
                                            ]
                                        }
                                    }
                                },
                                {
                                    "key": "process.pid",
                                    "value": {"intValue": "9876"}
                                },
                                {
                                    "key": "is.retried",
                                    "value": {"boolValue": True}
                                }
                            ],
                            "traceId": "5B8EFFF798038103D269A633813FC60C",
                            "spanId": "EEE19B7EC3C1B174"
                        }
                    ]
                }
            ]
        }
    ]
}

LARGE_BATCH_OTEL_PAYLOAD = {
    "resourceLogs": [
        {
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "batch-service"}}
                ]
            },
            "scopeLogs": [
                {
                    "logRecords": [
                        {
                            "timeUnixNano": "1682124012000000000",
                            "severityNumber": 9,
                            "severityText": "INFO",
                            "body": {"stringValue": "Log 1"},
                            "attributes": [{"key": "index", "value": {"intValue": "1"}}]
                        },
                        {
                            "timeUnixNano": "1682124013000000000",
                            "severityNumber": 9,
                            "severityText": "INFO",
                            "body": {"stringValue": "Log 2"},
                            "attributes": [{"key": "index", "value": {"intValue": "2"}}]
                        }
                    ]
                }
            ]
        }
    ]
}
