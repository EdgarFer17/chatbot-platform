from fastapi.testclient import TestClient

HEADERS = {"X-Admin-Key": "test-admin-key"}


def create_tenant(client: TestClient, name: str, slug: str) -> dict:
    response = client.post("/v1/admin/tenants", headers=HEADERS, json={"name": name, "slug": slug})
    assert response.status_code == 201
    return response.json()


def create_environment(client: TestClient, tenant_id: str) -> dict:
    response = client.post(f"/v1/admin/tenants/{tenant_id}/environments", headers=HEADERS, json={"name": "Homologação", "slug": "sandbox", "kind": "sandbox"})
    assert response.status_code == 201
    return response.json()


def test_admin_key_is_required(client: TestClient) -> None:
    assert client.get("/v1/admin/tenants").status_code == 422
    assert client.get("/v1/admin/tenants", headers={"X-Admin-Key": "incorrect"}).status_code == 401


def test_create_complete_tenant_structure(client: TestClient) -> None:
    tenant = create_tenant(client, "FAFIC", "fafic")
    environment = create_environment(client, tenant["id"])
    assistant = client.post(f"/v1/admin/tenants/{tenant['id']}/environments/{environment['id']}/assistants", headers=HEADERS, json={"name": "Assistente FAFIC", "slug": "atendimento", "system_prompt": "Responda com base no conhecimento institucional."})
    assert assistant.status_code == 201
    assert assistant.json()["tenant_id"] == tenant["id"]

    key = client.post(f"/v1/admin/tenants/{tenant['id']}/environments/{environment['id']}/api-keys", headers=HEADERS, json={"name": "Site institucional"})
    assert key.status_code == 201
    assert key.json()["key"].startswith("cbp_")
    keys = client.get(f"/v1/admin/tenants/{tenant['id']}/environments/{environment['id']}/api-keys", headers=HEADERS).json()
    assert len(keys) == 1
    assert "key" not in keys[0]
    assert "key_hash" not in keys[0]


def test_resources_cannot_cross_tenant_boundary(client: TestClient) -> None:
    fafic = create_tenant(client, "FAFIC", "fafic")
    another = create_tenant(client, "Empresa Exemplo", "empresa-exemplo")
    environment = create_environment(client, fafic["id"])
    response = client.post(f"/v1/admin/tenants/{another['id']}/environments/{environment['id']}/assistants", headers=HEADERS, json={"name": "Invasor", "slug": "invasor", "system_prompt": ""})
    assert response.status_code == 404


def test_duplicate_slug_returns_conflict(client: TestClient) -> None:
    create_tenant(client, "FAFIC", "fafic")
    response = client.post("/v1/admin/tenants", headers=HEADERS, json={"name": "Outra FAFIC", "slug": "fafic"})
    assert response.status_code == 409


def test_administrative_actions_are_audited_without_sensitive_payloads(client: TestClient) -> None:
    tenant = create_tenant(client, "Instituição Auditada", "instituicao-auditada")
    environment = create_environment(client, tenant["id"])
    created = client.post(
        f"/v1/admin/tenants/{tenant['id']}/environments/{environment['id']}/api-keys",
        headers=HEADERS,
        json={"name": "Integração auditada"},
    )
    assert created.status_code == 201
    secret = created.json()["key"]
    logs = client.get(f"/v1/admin/audit-logs?tenant_id={tenant['id']}", headers=HEADERS).json()
    assert [item["action"] for item in logs][:3] == ["api_key.created", "environment.created", "tenant.created"]
    assert all(secret not in str(item) for item in logs)
    assert all("content" not in item for item in logs)


def test_update_monthly_quota(client: TestClient) -> None:
    tenant = create_tenant(client, "Cliente com Cota", "cliente-com-cota")
    response = client.patch(f"/v1/admin/tenants/{tenant['id']}/quota", headers=HEADERS, json={"monthly_message_limit": 2500})
    assert response.status_code == 200
    assert response.json()["monthly_message_limit"] == 2500


def test_manage_and_publish_knowledge(client: TestClient) -> None:
    tenant = create_tenant(client, "FAFIC", "fafic")
    environment = create_environment(client, tenant["id"])
    assistant = client.post(
        f"/v1/admin/tenants/{tenant['id']}/environments/{environment['id']}/assistants",
        headers=HEADERS,
        json={"name": "Assistente FAFIC", "slug": "atendimento", "system_prompt": ""},
    ).json()
    path = f"/v1/admin/tenants/{tenant['id']}/environments/{environment['id']}/assistants/{assistant['id']}/knowledge"
    created = client.post(path, headers=HEADERS, json={"title": "Matrícula", "content": "O processo de matrícula começa pelo portal acadêmico da instituição."})
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    published = client.post(f"{path}/{created.json()['id']}/publish", headers=HEADERS)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert len(client.get(path, headers=HEADERS).json()) == 1
