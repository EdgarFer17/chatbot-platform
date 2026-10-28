"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowClockwise,
  ChatCircleText,
  Eye,
  Sparkle,
  WarningCircle,
} from "@phosphor-icons/react";

type ConversationSummary = {
  id: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  message_count: number;
  first_message: string | null;
  last_message: string | null;
  last_role: string | null;
  confidence: number | null;
};

type Citation = {
  document_id: string;
  title: string;
  url: string | null;
  excerpt: string;
};

type MessageDetail = {
  id: string;
  role: "user" | "assistant";
  content: string;
  confidence: number | null;
  citations: Citation[] | null;
  created_at: string | null;
};

type ConversationDetail = {
  id: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  external_user_id: string | null;
  messages: MessageDetail[];
};

async function fetchConversations(): Promise<{
  total: number;
  conversations: ConversationSummary[];
}> {
  const res = await fetch("/api/platform/institution/conversations?limit=60", {
    signal: AbortSignal.timeout(15000),
  });
  if (res.status === 401) {
    window.location.assign("/login");
    throw new Error("Entre novamente para continuar.");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao listar conversas.");
  return data;
}

async function fetchConversationDetail(id: string): Promise<ConversationDetail> {
  const res = await fetch(`/api/platform/institution/conversations/${id}`, {
    signal: AbortSignal.timeout(15000),
  });
  if (res.status === 401) {
    window.location.assign("/login");
    throw new Error("Entre novamente para continuar.");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao carregar conversa.");
  return data;
}

export function ConversationsPanel() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchConversations();
      setConversations(data.conversations);
      setTotal(data.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar conversas.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openConversation = async (id: string) => {
    setSelectedId(id);
    setDetailLoading(true);
    setDetail(null);
    try {
      const d = await fetchConversationDetail(id);
      setDetail(d);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao abrir conversa.");
      setSelectedId(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDialog = () => {
    setSelectedId(null);
    setDetail(null);
  };

  const filtered = conversations.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      c.id.toLowerCase().includes(q) ||
      (c.first_message && c.first_message.toLowerCase().includes(q)) ||
      (c.last_message && c.last_message.toLowerCase().includes(q))
    );
  });

  return (
    <div className="f-app">
      <header className="f-header">
        <Link className="f-brand" href="/">
          <strong>FAFIC</strong>
          <span>Assistente institucional</span>
        </Link>
        <Link href="/" className="f-logout">
          Voltar ao controle
        </Link>
      </header>

      <main className="f-control d-page">
        <p className="f-eyebrow">ATENDIMENTOS REALIZADOS</p>
        <div className="m-header-row">
          <div>
            <h1>Conversas dos visitantes</h1>
            <p className="f-intro">
              Consulte as perguntas recebidas no site, as respostas dadas pelo assistente e as fontes citadas.
            </p>
          </div>
          <button
            className="f-button d-secondary m-refresh-btn"
            disabled={refreshing || loading}
            onClick={() => {
              setRefreshing(true);
              void load();
            }}
          >
            <ArrowClockwise size={16} className={refreshing ? "m-spin" : ""} />
            {refreshing ? "Atualizando…" : "Atualizar"}
          </button>
        </div>

        <nav className="d-navigation" aria-label="Navegação do painel">
          <Link href="/">Controle</Link>
          <Link href="/documentos">Documentos</Link>
          <Link href="/metricas">Métricas</Link>
          <Link href="/conversas" aria-current="page">
            Conversas
          </Link>
          <a href="/demo.html" target="_blank" rel="noopener noreferrer">
            Testar chat ↗
          </a>
        </nav>

        {error && (
          <div className="f-alert error" role="alert">
            <WarningCircle size={20} />
            <span>{error}</span>
            <button
              onClick={() => {
                setLoading(true);
                void load();
              }}
            >
              Tentar novamente
            </button>
          </div>
        )}

        <section className="d-overview">
          <span>
            <strong>{total}</strong> atendimentos registrados
          </span>
          <span>Privacidade preservada: sem armazenamento de dados pessoais</span>
        </section>

        <section className="f-card">
          <div className="d-section-heading">
            <h2>Histórico recente</h2>
            <small>{filtered.length} conversa(s) exibida(s)</small>
          </div>

          <div className="d-filters">
            <label style={{ flex: 1 }}>
              Buscar na conversa
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Busque por palavras na pergunta ou resposta…"
              />
            </label>
          </div>

          {loading ? (
            <p role="status" className="f-loading">
              Carregando atendimentos…
            </p>
          ) : filtered.length === 0 ? (
            <p className="d-empty">
              {search
                ? "Nenhuma conversa corresponde ao termo pesquisado."
                : "Nenhum atendimento registrado ainda."}
            </p>
          ) : (
            <div className="c-list">
              {filtered.map((c) => {
                const dateStr = c.created_at
                  ? new Date(c.created_at).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "Data desconhecida";

                return (
                  <article className="c-row" key={c.id}>
                    <div className="c-icon-slot">
                      <ChatCircleText size={22} className="m-icon-blue" />
                    </div>
                    <div className="c-copy">
                      <div className="c-meta">
                        <time>{dateStr}</time>
                        <span
                          className={`d-badge ${
                            c.status === "active" ? "published" : ""
                          }`}
                        >
                          {c.status === "active" ? "Ativa" : "Encerrada"}
                        </span>
                        <span className="c-count">
                          {c.message_count} {c.message_count === 1 ? "mensagem" : "mensagens"}
                        </span>
                        {c.confidence !== null && (
                          <span
                            className="c-conf"
                            title={`Aderência às fontes: ${Math.round(c.confidence * 100)}%`}
                          >
                            <Sparkle size={12} />
                            {Math.round(c.confidence * 100)}% confiança
                          </span>
                        )}
                      </div>
                      <h3>
                        {c.first_message ? (
                          <>
                            <span className="c-user-label">Pergunta: </span>
                            &ldquo;{c.first_message}&rdquo;
                          </>
                        ) : (
                          <span className="c-no-msg">Conversa iniciada sem mensagens</span>
                        )}
                      </h3>
                      {c.last_message && c.last_message !== c.first_message && (
                        <p className="c-last-preview">
                          <strong>Última: </strong>
                          {c.last_message}
                        </p>
                      )}
                    </div>
                    <div className="d-actions">
                      <button
                        className="f-button d-secondary"
                        onClick={() => void openConversation(c.id)}
                      >
                        <Eye size={16} />
                        Abrir conversa
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <footer>FAFIC · Assistente institucional</footer>
      </main>

      {/* Modal de diálogo da conversa */}
      {selectedId && (
        <ConversationDialog
          loading={detailLoading}
          detail={detail}
          close={closeDialog}
        />
      )}
    </div>
  );
}

function ConversationDialog({
  loading,
  detail,
  close,
}: {
  loading: boolean;
  detail: ConversationDetail | null;
  close: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [close]);

  return (
    <dialog
      ref={dialogRef}
      className="d-dialog c-dialog"
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <header>
        <div>
          <h2>Atendimento virtual</h2>
          <small className="c-dialog-id">
            ID: {detail?.id?.slice(0, 8)} ·{" "}
            {detail?.created_at
              ? new Date(detail.created_at).toLocaleString("pt-BR")
              : ""}
          </small>
        </div>
        <button onClick={close} aria-label="Fechar diálogo">
          ×
        </button>
      </header>

      <div className="c-dialog-body">
        {loading ? (
          <p className="f-loading">Carregando mensagens da conversa…</p>
        ) : detail && detail.messages.length === 0 ? (
          <p className="d-empty">Esta conversa não registrou mensagens.</p>
        ) : detail ? (
          <div className="c-thread">
            {detail.messages.map((m) => {
              const isUser = m.role === "user";
              const timeStr = m.created_at
                ? new Date(m.created_at).toLocaleTimeString("pt-BR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "";

              return (
                <div
                  key={m.id}
                  className={`c-msg-row ${isUser ? "user" : "assistant"}`}
                >
                  <div className="c-bubble">
                    <div className="c-bubble-header">
                      <span className="c-bubble-sender">
                        {isUser ? "Visitante do site" : "Assistente FAFIC"}
                      </span>
                      {timeStr && <time>{timeStr}</time>}
                    </div>
                    <div className="c-bubble-content">{m.content}</div>

                    {!isUser && m.confidence !== null && (
                      <div className="c-bubble-conf">
                        <Sparkle size={12} />
                        Confiança da resposta: {Math.round(m.confidence * 100)}%
                      </div>
                    )}

                    {!isUser && m.citations && m.citations.length > 0 && (
                      <details className="c-sources-details">
                        <summary>
                          Fontes consultadas ({m.citations.length})
                        </summary>
                        <div className="c-sources-list">
                          {m.citations.map((c, i) => (
                            <div key={i} className="c-source-item">
                              <b>{c.title}</b>
                              {c.excerpt && <p>&ldquo;{c.excerpt}&rdquo;</p>}
                              {c.url && (
                                <a
                                  href={c.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  Ver documento original ↗
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      <footer className="c-dialog-footer">
        <button className="f-button d-secondary" onClick={close}>
          Fechar visualização
        </button>
      </footer>
    </dialog>
  );
}
