import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_api_key
from app.modules.knowledge.embeddings import generate_embeddings
from app.modules.platform.models import ApiKey, Assistant, Environment, EnvironmentKind, KnowledgeChunk, KnowledgeDocument, KnowledgeStatus, Tenant


def seed_client(database: Session) -> tuple[str, str]:
    tenant = Tenant(name="FAFIC", slug="fafic")
    database.add(tenant)
    database.flush()
    environment = Environment(tenant_id=tenant.id, name="Homologação", slug="sandbox", kind=EnvironmentKind.SANDBOX)
    database.add(environment)
    database.flush()
    assistant = Assistant(tenant_id=tenant.id, environment_id=environment.id, name="Assistente FAFIC", slug="atendimento", system_prompt="")
    raw_key, prefix, key_hash = create_api_key()
    database.add(assistant)
    database.flush()
    database.add(ApiKey(tenant_id=tenant.id, environment_id=environment.id, name="Site", key_prefix=prefix, key_hash=key_hash))
    database.commit()
    return raw_key, str(assistant.id)


def test_public_conversation_flow(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    headers = {"Authorization": f"Bearer {raw_key}"}
    created = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id, "external_user_id": "student-42"})
    assert created.status_code == 201
    session_id = created.json()["id"]

    exchange = client.post(f"/v1/sessions/{session_id}/messages", headers=headers, json={"content": "Como faço minha matrícula?"})
    assert exchange.status_code == 201
    assert exchange.json()["user_message"]["role"] == "user"
    assert "base de conhecimento" in exchange.json()["assistant_message"]["content"]

    history = client.get(f"/v1/sessions/{session_id}/messages", headers=headers)
    assert history.status_code == 200
    assert [message["role"] for message in history.json()] == ["user", "assistant"]

    assert client.post(f"/v1/sessions/{session_id}/close", headers=headers).status_code == 200
    assert client.post(f"/v1/sessions/{session_id}/messages", headers=headers, json={"content": "Outra pergunta"}).status_code == 409


def test_invalid_api_key_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/sessions", headers={"Authorization": "Bearer cbp_invalid_key"}, json={"assistant_id": "21f3aa62-2064-46ad-b7bc-62a0335ae26f"})
    assert response.status_code == 401


def test_grounded_response_returns_citation(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    database.add(KnowledgeDocument(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id, assistant_id=assistant.id, title="Matrícula online", content="A matrícula deve ser realizada no portal acadêmico usando CPF e senha do estudante.", original_url="https://faculdade.example/docs/matricula", status=KnowledgeStatus.PUBLISHED))
    database.commit()
    headers = {"Authorization": f"Bearer {raw_key}"}
    session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()
    exchange = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Como realizar minha matrícula?"})
    assert exchange.status_code == 201
    assert exchange.json()["citations"][0]["title"] == "Matrícula online"
    assert exchange.json()["confidence"] > 0


def test_monthly_quota_counts_interactions_and_blocks_excess(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    tenant = database.get(Tenant, assistant.tenant_id)
    tenant.monthly_message_limit = 1
    database.commit()
    headers = {"Authorization": f"Bearer {raw_key}"}
    session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()

    first = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Primeira pergunta"})
    second = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Segunda pergunta"})

    assert first.status_code == 201
    assert second.status_code == 429
    assert len(client.get(f"/v1/sessions/{session['id']}/messages", headers=headers).json()) == 2
    usage = client.get(f"/v1/admin/tenants/{tenant.id}/usage", headers={"X-Admin-Key": "test-admin-key"}).json()
    assert usage["interactions_used"] == 1
    assert usage["remaining"] == 0
    assert usage["usage_percentage"] == 100


def test_follow_up_uses_only_recent_history_from_same_session(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    database.add(KnowledgeDocument(
        tenant_id=assistant.tenant_id,
        environment_id=assistant.environment_id,
        assistant_id=assistant.id,
        title="Matrícula online 2026",
        content="A matrícula online deve ser concluída no Portal Acadêmico. O prazo final para concluir a matrícula é 10 de setembro de 2026.",
        original_url="https://faculdade.example/matricula-2026",
        status=KnowledgeStatus.PUBLISHED,
    ))
    database.commit()
    headers = {"Authorization": f"Bearer {raw_key}"}
    first_session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()
    client.post(f"/v1/sessions/{first_session['id']}/messages", headers=headers, json={"content": "Quero informações sobre a matrícula online de 2026"})
    follow_up = client.post(f"/v1/sessions/{first_session['id']}/messages", headers=headers, json={"content": "E até quando?"})
    assert follow_up.status_code == 201
    assert follow_up.json()["citations"][0]["title"] == "Matrícula online 2026"
    assert "10 de setembro" in follow_up.json()["assistant_message"]["content"]

    isolated_session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()
    isolated = client.post(f"/v1/sessions/{isolated_session['id']}/messages", headers=headers, json={"content": "E até quando?"})
    assert isolated.status_code == 201
    assert isolated.json()["citations"] == []


def test_widget_uses_short_lived_origin_bound_token(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    issued = client.post(
        "/v1/widget/tokens",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={"assistant_id": assistant_id, "allowed_origin": "https://www.fafic.example"},
    )
    assert issued.status_code == 201
    assert issued.json()["token"].startswith("wgt_")
    assert issued.json()["expires_in"] == 900
    widget_headers = {"Authorization": f"Bearer {issued.json()['token']}", "Origin": "https://www.fafic.example"}
    created = client.post("/v1/sessions", headers=widget_headers, json={"assistant_id": assistant_id, "external_user_id": "browser-test"})
    assert created.status_code == 201
    assert client.post(f"/v1/sessions/{created.json()['id']}/messages", headers=widget_headers, json={"content": "Olá"}).status_code == 201
    wrong_origin = {"Authorization": f"Bearer {issued.json()['token']}", "Origin": "https://evil.example"}
    assert client.get(f"/v1/sessions/{created.json()['id']}", headers=wrong_origin).status_code == 401


def test_social_and_incomplete_messages_do_not_repeat_document_answer(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    database.add(KnowledgeDocument(
        tenant_id=assistant.tenant_id,
        environment_id=assistant.environment_id,
        assistant_id=assistant.id,
        title="Regimento Interno",
        content="A matrícula é realizada no Portal Acadêmico.",
        status=KnowledgeStatus.PUBLISHED,
    ))
    database.commit()
    headers = {"Authorization": f"Bearer {raw_key}"}
    session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()

    first = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Como faço minha matrícula?"})
    thanks = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Entendi, obrigado"})
    incomplete = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "a"})

    assert first.status_code == 201
    assert thanks.json()["citations"] == []
    assert "Por nada" in thanks.json()["assistant_message"]["content"]
    assert incomplete.json()["citations"] == []
    assert "mais de detalhe" in incomplete.json()["assistant_message"]["content"]


def test_table_of_contents_chunk_is_penalized(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    document = KnowledgeDocument(
        tenant_id=assistant.tenant_id,
        environment_id=assistant.environment_id,
        assistant_id=assistant.id,
        title="Regimento Interno",
        content="conteúdo",
        status=KnowledgeStatus.PUBLISHED,
    )
    database.add(document)
    database.flush()
    database.add_all([
        KnowledgeChunk(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id, assistant_id=assistant.id, document_id=document.id, position=0, content="DA MATRÍCULA ........................................ 20\nDo Ajustamento de Matrícula ........................ 21\nDo Trancamento de Matrícula ........................ 22"),
        KnowledgeChunk(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id, assistant_id=assistant.id, document_id=document.id, position=1, content="A matrícula dos estudantes deve ser realizada pelo Portal Acadêmico no período previsto no calendário institucional."),
    ])
    database.commit()
    headers = {"Authorization": f"Bearer {raw_key}"}
    session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()
    response = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Como faço minha matrícula?"})

    assert response.status_code == 201
    assert "Portal Acadêmico" in response.json()["assistant_message"]["content"]


def test_pdf_line_breaks_do_not_interrupt_extractive_answer(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    database.add(KnowledgeDocument(
        tenant_id=assistant.tenant_id,
        environment_id=assistant.environment_id,
        assistant_id=assistant.id,
        title="Regimento Interno",
        content="Art. 73. A matrícula inicial, ato formal de ingresso no curso e de vinculação à\nFaculdade, será realizada no prazo do calendário letivo e deverá ser requerida pelo\ninteressado. I - Ter sido aprovado no processo seletivo; II - Apresentar a documentação indispensável;",
        status=KnowledgeStatus.PUBLISHED,
    ))
    database.commit()
    headers = {"Authorization": f"Bearer {raw_key}"}
    session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()
    response = client.post(f"/v1/sessions/{session['id']}/messages", headers=headers, json={"content": "Como faço minha matrícula?"})
    answer = response.json()["assistant_message"]["content"]

    assert "vinculação à Faculdade" in answer
    assert "deverá ser requerida pelo interessado" in answer


def test_semantic_search_retrieves_synonym_chunk(client: TestClient, database: Session) -> None:
    raw_key, assistant_id = seed_client(database)
    assistant = database.get(Assistant, uuid.UUID(assistant_id))
    chunk_text = "O numero de contato e atendimento telefonico da faculdade e 3322-1100."
    embeddings = generate_embeddings([chunk_text])
    document = KnowledgeDocument(
        tenant_id=assistant.tenant_id,
        environment_id=assistant.environment_id,
        assistant_id=assistant.id,
        title="Canais de Atendimento",
        content=chunk_text,
        status=KnowledgeStatus.PUBLISHED,
    )
    database.add(document)
    database.flush()
    database.add(KnowledgeChunk(
        tenant_id=assistant.tenant_id,
        environment_id=assistant.environment_id,
        assistant_id=assistant.id,
        document_id=document.id,
        position=0,
        content=chunk_text,
        embedding=embeddings[0],
    ))
    database.commit()

    headers = {"Authorization": f"Bearer {raw_key}"}
    session = client.post("/v1/sessions", headers=headers, json={"assistant_id": assistant_id}).json()
    response = client.post(
        f"/v1/sessions/{session['id']}/messages",
        headers=headers,
        json={"content": "Qual o telefone da instituicao?"},
    )
    assert response.status_code == 201
    assert "3322-1100" in response.json()["assistant_message"]["content"]
    assert len(response.json()["citations"]) > 0
    assert response.json()["citations"][0]["title"] == "Canais de Atendimento"

