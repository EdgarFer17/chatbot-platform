import pytest

from app.modules.knowledge.ingestion import IngestionError, discover_document_urls, discover_sitemap_urls, extract_document, validate_public_url


def test_extract_html_and_discover_same_domain_documents() -> None:
    html = b"""<html><head><title>Normas</title></head><body><script>ignore()</script><h1>Documentos normativos</h1><p>Conteudo institucional para estudantes.</p><a href='/docs/regimento.pdf'>Regimento</a><a href='https://other.example/file.pdf'>Externo</a></body></html>"""
    extracted = extract_document(html, "text/html", "https://faculdade.example/documentos/")
    assert extracted.title == "Documentos normativos"
    assert "Conteudo institucional" in extracted.content
    links = discover_document_urls(html, "https://faculdade.example/documentos/", "faculdade.example")
    assert links == [("https://faculdade.example/docs/regimento.pdf", "Regimento")]


def test_documentation_page_uses_main_content_and_discovers_extensionless_routes() -> None:
    html = b"""<html><head><title>Portal</title></head><body><nav>Menu repetido</nav><main><h1>Entrada de nota</h1><p>Procedimento completo da rotina financeira.</p><a href='/docs/financeiro/entrada-nota'>Proxima rotina</a></main><footer>Rodape repetido</footer></body></html>"""
    extracted = extract_document(html, "text/html", "https://docs.example/docs/financeiro/")
    assert extracted.title == "Entrada de nota"
    assert "Procedimento completo" in extracted.content
    assert "Menu repetido" not in extracted.content
    assert "Rodape repetido" not in extracted.content
    links = discover_document_urls(html, "https://docs.example/docs/financeiro/", "docs.example")
    assert links == [("https://docs.example/docs/financeiro/entrada-nota", "Proxima rotina")]


def test_private_network_url_is_rejected() -> None:
    with pytest.raises(IngestionError, match="não é uma fonte pública"):
        validate_public_url("http://127.0.0.1/internal")


def test_sitemap_keeps_only_authorized_domain() -> None:
    sitemap = b"""<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>https://docs.example/docs/matricula</loc></url><url><loc>https://other.example/private</loc></url></urlset>"""
    assert discover_sitemap_urls(sitemap, "docs.example") == ["https://docs.example/docs/matricula"]


def test_title_only_image_page_is_rejected() -> None:
    html = b"<html><body><main><h1>Comunicado publicado somente como imagem</h1></main></body></html>"
    with pytest.raises(IngestionError, match="apenas em imagens"):
        extract_document(html, "text/html", "https://faculdade.example/comunicado")


def test_discovery_ignores_links_outside_main_content() -> None:
    html = b"""<html><body><nav><a href='/noticias'>Noticias</a></nav><main><p>Documentos oficiais desta secao para consulta da comunidade academica.</p><a href='/uploads/regimento.pdf'>Regimento</a></main></body></html>"""
    assert discover_document_urls(html, "https://faculdade.example/documentos/", "faculdade.example") == [("https://faculdade.example/uploads/regimento.pdf", "Regimento")]
