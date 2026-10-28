from fastapi.testclient import TestClient


def test_public_openapi_contract_is_stable(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == "1.0.0-rc.1"
    operation_ids = [operation["operationId"] for methods in schema["paths"].values() for method, operation in methods.items() if method.lower() in {"get", "post", "patch", "delete"}]
    assert len(operation_ids) == len(set(operation_ids))
    assert schema["paths"]["/v1/sessions/{session_id}/messages"]["post"]["operationId"] == "send_message"
    assert "429" in schema["paths"]["/v1/sessions/{session_id}/messages"]["post"]["responses"]
    assert schema["paths"]["/v1/sessions"]["post"]["operationId"] == "create_session"
