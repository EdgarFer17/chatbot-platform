"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowClockwise,
  ChartBar,
  ChatCircle,
  Gauge,
  Lightning,
  Stack,
  WarningCircle,
} from "@phosphor-icons/react";

type Metrics = {
  bot_active: boolean;
  bot_name: string;
  interactions_used: number;
  monthly_limit: number;
  usage_percentage: number;
  sessions_total: number;
  sessions_month: number;
  total_user_messages: number;
  published_documents: number;
  draft_documents: number;
  total_sources: number;
  confidence_average: number | null;
  daily_messages: { date: string; count: number }[];
  top_cited_documents: { title: string; count: number }[];
};

async function fetchMetrics(): Promise<Metrics> {
  const res = await fetch("/api/platform/institution/metrics", {
    signal: AbortSignal.timeout(15000),
  });
  if (res.status === 401) {
    window.location.assign("/login");
    throw new Error("Entre novamente para continuar.");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao carregar métricas.");
  return data;
}

export function MetricsPanel() {
  const [data, setData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const result = await fetchMetrics();
      setData(result);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dados.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = () => {
    setRefreshing(true);
    void load();
  };

  const maxDailyCount = data?.daily_messages?.length
    ? Math.max(...data.daily_messages.map((d) => d.count), 1)
    : 1;

  const maxCitedCount = data?.top_cited_documents?.length
    ? Math.max(...data.top_cited_documents.map((d) => d.count), 1)
    : 1;

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
        <p className="f-eyebrow">RELATÓRIO & DESEMPENHO</p>
        <div className="m-header-row">
          <div>
            <h1>Métricas do assistente</h1>
            <p className="f-intro">
              Acompanhe o volume de atendimentos, consumo da cota e a qualidade das respostas.
            </p>
          </div>
          <button
            className="f-button d-secondary m-refresh-btn"
            disabled={refreshing || loading}
            onClick={refresh}
          >
            <ArrowClockwise size={16} className={refreshing ? "m-spin" : ""} />
            {refreshing ? "Atualizando…" : "Atualizar dados"}
          </button>
        </div>

        <nav className="d-navigation" aria-label="Navegação do painel">
          <Link href="/">Controle</Link>
          <Link href="/documentos">Documentos</Link>
          <Link href="/metricas" aria-current="page">
            Métricas
          </Link>
          <Link href="/conversas">Conversas</Link>
          <a href="/demo.html" target="_blank" rel="noopener noreferrer">
            Testar chat ↗
          </a>
        </nav>

        {error && (
          <div className="f-alert error" role="alert">
            <WarningCircle size={20} />
            <span>{error}</span>
            <button onClick={refresh}>Tentar novamente</button>
          </div>
        )}

        {loading ? (
          <p role="status" className="f-loading">
            Carregando métricas…
          </p>
        ) : data ? (
          <>
            <div className="m-kpi-grid">
              <article className="m-kpi-card">
                <div className="m-kpi-header">
                  <span>MENSAGENS DO MÊS</span>
                  <Lightning size={20} className="m-icon-gold" />
                </div>
                <div className="m-kpi-val">
                  <strong>{data.interactions_used.toLocaleString("pt-BR")}</strong>
                  <small>/ {data.monthly_limit.toLocaleString("pt-BR")}</small>
                </div>
                <div className="m-progress-bar">
                  <div
                    className="m-progress-fill"
                    style={{ width: `${Math.min(100, data.usage_percentage)}%` }}
                  />
                </div>
                <span className="m-kpi-sub">
                  {data.usage_percentage}% da cota mensal utilizada
                </span>
              </article>

              <article className="m-kpi-card">
                <div className="m-kpi-header">
                  <span>CONVERSAS INICIADAS</span>
                  <ChatCircle size={20} className="m-icon-blue" />
                </div>
                <div className="m-kpi-val">
                  <strong>{data.sessions_month.toLocaleString("pt-BR")}</strong>
                  <small>este mês</small>
                </div>
                <span className="m-kpi-sub">
                  Total histórico: {data.sessions_total.toLocaleString("pt-BR")} atendimentos
                </span>
              </article>

              <article className="m-kpi-card">
                <div className="m-kpi-header">
                  <span>PERGUNTAS FEITAS</span>
                  <ChartBar size={20} className="m-icon-blue" />
                </div>
                <div className="m-kpi-val">
                  <strong>{data.total_user_messages.toLocaleString("pt-BR")}</strong>
                </div>
                <span className="m-kpi-sub">
                  Perguntas de visitantes recebidas
                </span>
              </article>

              <article className="m-kpi-card">
                <div className="m-kpi-header">
                  <span>CONFIANÇA MÉDIA</span>
                  <Gauge size={20} className="m-icon-gold" />
                </div>
                <div className="m-kpi-val">
                  <strong>
                    {data.confidence_average !== null
                      ? `${Math.round(data.confidence_average * 100)}%`
                      : "—"}
                  </strong>
                </div>
                <span className="m-kpi-sub">
                  {data.confidence_average !== null && data.confidence_average >= 0.7
                    ? "Excelente aderência aos documentos"
                    : data.confidence_average !== null
                    ? "Respostas baseadas nos trechos encontrados"
                    : "Ainda sem dados suficientes"}
                </span>
              </article>

              <article className="m-kpi-card">
                <div className="m-kpi-header">
                  <span>BASE DE CONHECIMENTO</span>
                  <Stack size={20} className="m-icon-blue" />
                </div>
                <div className="m-kpi-val">
                  <strong>{data.published_documents}</strong>
                  <small>publicados</small>
                </div>
                <span className="m-kpi-sub">
                  {data.draft_documents} rascunhos · {data.total_sources} fontes ativas
                </span>
              </article>
            </div>

            <section className="f-card m-section">
              <div className="d-section-heading">
                <div>
                  <h2>Atividade recente</h2>
                  <p className="m-card-desc">
                    Perguntas respondidas nos últimos 14 dias
                  </p>
                </div>
              </div>

              {data.daily_messages.length === 0 ||
              data.daily_messages.every((d) => d.count === 0) ? (
                <div className="d-empty">
                  Nenhuma mensagem registrada nos últimos 14 dias.
                </div>
              ) : (
                <div className="m-chart-container">
                  <div className="m-chart-bars">
                    {data.daily_messages.map((d) => {
                      const heightPercent = Math.max(
                        6,
                        Math.round((d.count / maxDailyCount) * 100)
                      );
                      const parts = d.date.split("-");
                      const label = parts.length === 3 ? `${parts[2]}/${parts[1]}` : d.date;
                      return (
                        <div
                          className="m-bar-col"
                          key={d.date}
                          title={`${label}: ${d.count} mensagem(ns)`}
                        >
                          <span className="m-bar-count">{d.count}</span>
                          <div
                            className="m-bar-fill"
                            style={{ height: `${heightPercent}%` }}
                          />
                          <span className="m-bar-date">{label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>

            <section className="f-card m-section">
              <h2>Documentos mais consultados pelo assistente</h2>
              <p className="m-card-desc">
                Fontes que mais frequentemente embasaram respostas aos visitantes.
              </p>

              {data.top_cited_documents.length === 0 ? (
                <div className="d-empty">
                  Ainda não há citações registradas nas respostas recentes.
                </div>
              ) : (
                <div className="m-cited-list">
                  {data.top_cited_documents.map((doc, idx) => {
                    const pct = Math.round((doc.count / maxCitedCount) * 100);
                    return (
                      <div className="m-cited-item" key={doc.title}>
                        <span className="m-cited-rank">{idx + 1}</span>
                        <div className="m-cited-info">
                          <div className="m-cited-header">
                            <span className="m-cited-title">{doc.title}</span>
                            <span className="m-cited-count">
                              {doc.count} {doc.count === 1 ? "citação" : "citações"}
                            </span>
                          </div>
                          <div className="m-cited-track">
                            <div
                              className="m-cited-fill"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        ) : null}

        <footer>FAFIC · Assistente institucional</footer>
      </main>
    </div>
  );
}
