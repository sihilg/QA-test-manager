import { FormEvent, useEffect, useState } from "react";

import type { Project } from "./Projects";

type User = { id: number; name: string; email: string; role: "ADMIN" | "TESTER" | "DEV" };
type Proposal = {
  id: number;
  proposal_key: string;
  category: "POSITIVE" | "NEGATIVE" | "BOUNDARY";
  status: "DRAFT" | "APPROVED" | "REJECTED" | "CONVERTED";
  payload: { title: string; requirement: string; description: string; expected_result: string };
  converted_test_case_id: number | null;
  duplicate: boolean;
};
type Exchange = { public_id: string; json_url: string; markdown_url: string };

export function EvaWorkspace({ user, project, csrfToken, onCases, onBack, onLogout }: { user: User; project: Project; csrfToken: string; onCases: () => void; onBack: () => void; onLogout: () => void }) {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [exchange, setExchange] = useState<Exchange | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const canEdit = user.role !== "DEV";

  async function loadProposals() {
    const response = await fetch(`/api/projects/${project.id}/eva/proposals`, { credentials: "include" });
    if (!response.ok) throw new Error(await responseMessage(response));
    setProposals((await response.json()) as Proposal[]);
  }

  useEffect(() => {
    let active = true;
    fetch(`/api/projects/${project.id}/eva/proposals`, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error("Não foi possível carregar as propostas.");
        return response.json() as Promise<Proposal[]>;
      })
      .then((items) => { if (active) setProposals(items); })
      .catch((reason: unknown) => {
        if (active) {
          setError(true);
          setMessage(reason instanceof Error ? reason.message : "Não foi possível carregar as propostas.");
        }
      });
    return () => { active = false; };
  }, [project.id]);

  async function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(false); setMessage("");
    const form = new FormData(event.currentTarget);
    const response = await apiRequest(`/api/projects/${project.id}/eva/exchanges`, "POST", csrfToken, { title: form.get("title"), content: form.get("content") });
    if (response.ok) {
      setExchange((await response.json()) as Exchange);
      setMessage("Pacote preparado. Faça download e use-o no seu cowork com a Eva.");
    } else { setError(true); setMessage(await responseMessage(response)); }
    setBusy(false);
  }

  async function importFile(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError(false); setMessage("");
    try {
      const raw = JSON.parse(await file.text()) as { exchange_id?: string };
      if (!raw.exchange_id) throw new Error("O ficheiro não contém exchange_id.");
      const response = await apiRequest(`/api/eva/exchanges/${raw.exchange_id}/import`, "POST", csrfToken, raw);
      if (!response.ok) throw new Error(await responseMessage(response));
      await loadProposals();
      setMessage("Resposta importada. As propostas estão em rascunho para revisão humana.");
    } catch (reason) {
      setError(true); setMessage(reason instanceof Error ? reason.message : "JSON inválido.");
    } finally { setBusy(false); }
  }

  async function updateTitle(proposal: Proposal) {
    const title = window.prompt("Novo título", proposal.payload.title)?.trim();
    if (!title || title === proposal.payload.title) return;
    await act(`/api/eva/proposals/${proposal.id}`, "PATCH", { title }, "Título atualizado.");
  }

  async function act(url: string, method: string, body: object | undefined, success: string) {
    setBusy(true); setError(false); setMessage("");
    const response = await apiRequest(url, method, csrfToken, body);
    if (response.ok) { await loadProposals(); setMessage(success); }
    else { setError(true); setMessage(await responseMessage(response)); }
    setBusy(false);
  }

  return <div className="workspace">
    <header className="app-header"><div><p className="eyebrow">Projeto · {project.name}</p><h1>Eva</h1><p className="welcome">Cowork local com revisão humana antes de criar casos.</p></div><div className="header-actions"><button type="button" className="secondary" onClick={onCases}>Casos de teste</button><button type="button" className="secondary" onClick={onBack}>Projetos</button><button type="button" className="secondary" onClick={onLogout}>Terminar sessão</button></div></header>

    {canEdit && !project.is_archived && <section className="panel"><h2>1. Preparar pedido</h2><form className="project-form" onSubmit={prepare}><label>Título<input name="title" minLength={1} maxLength={240} required /></label><label>Requisito ou contexto<textarea name="content" rows={7} maxLength={20000} required /></label><button type="submit" disabled={busy}>Preparar pacote</button></form>{exchange && <div className="eva-downloads"><a className="export-link" href={`/api${exchange.json_url}`}>Download JSON</a><a className="export-link" href={`/api${exchange.markdown_url}`}>Download Markdown</a></div>}</section>}

    {canEdit && <section className="panel"><h2>2. Importar resposta</h2><p className="summary">Selecione o JSON devolvido pela Eva. Nada é enviado automaticamente ao ChatGPT.</p><label className="file-picker">Resposta JSON<input aria-label="Resposta JSON" type="file" accept="application/json,.json" disabled={busy} onChange={(event) => void importFile(event.target.files?.[0])} /></label></section>}

    <section className="panel"><div className="section-heading"><div><h2>3. Rever propostas</h2><p>{proposals.length} proposta(s)</p></div><button type="button" className="tertiary" onClick={() => void loadProposals()}>Atualizar</button></div>{message && <p className={error ? "error" : "notice"} role="status">{message}</p>}{proposals.length === 0 ? <p className="empty-state">Ainda não existem propostas importadas.</p> : <div className="proposal-grid">{proposals.map((proposal) => <article className="proposal-card" key={proposal.id}><div><span className="active-badge">{proposal.category}</span><span className={`proposal-status ${proposal.status.toLowerCase()}`}>{proposal.status}</span></div><h3>{proposal.payload.title}</h3><p>{proposal.payload.description}</p>{proposal.duplicate && <p className="error">Possível duplicado: altere o título ou rejeite antes de aprovar.</p>}{canEdit && proposal.status === "DRAFT" && <div className="card-actions"><button type="button" className="tertiary" disabled={busy} onClick={() => void updateTitle(proposal)}>Editar título</button><button type="button" className="danger" disabled={busy} onClick={() => void act(`/api/eva/proposals/${proposal.id}/reject`, "POST", undefined, "Proposta rejeitada.")}>Rejeitar</button><button type="button" disabled={busy || proposal.duplicate} onClick={() => void act(`/api/eva/proposals/${proposal.id}/approve`, "POST", undefined, "Proposta aprovada e convertida em caso de teste.")}>Aprovar</button></div>}</article>)}</div>}</section>
  </div>;
}

async function apiRequest(url: string, method: string, csrfToken: string, body?: object) {
  return fetch(url, { method, credentials: "include", headers: { "X-CSRF-Token": csrfToken, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
}

async function responseMessage(response: Response) {
  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  return typeof payload?.detail === "string" ? payload.detail : "Não foi possível concluir a operação.";
}
