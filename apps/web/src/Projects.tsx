import { FormEvent, useEffect, useState } from "react";

type User = { id: number; name: string; email: string; role: "ADMIN" | "TESTER" | "DEV" };
type Project = {
  id: number;
  name: string;
  description: string;
  is_archived: boolean;
  version: number;
};
type ProjectPage = { items: Project[]; total: number; offset: number; limit: number };

const PAGE_SIZE = 10;

export function Projects({ user, csrfToken, onLogout, onUsers }: { user: User; csrfToken: string; onLogout: () => void; onUsers: () => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<Project | null>(null);

  async function loadProjects(nextOffset = offset) {
    setStatus("loading");
    setMessage("");
    try {
      const response = await fetch(`/api/projects?offset=${nextOffset}&limit=${PAGE_SIZE}`, {
        credentials: "include",
      });
      if (!response.ok) throw new Error("Não foi possível carregar os projetos.");
      const page = (await response.json()) as ProjectPage;
      setProjects(page.items);
      setTotal(page.total);
      setOffset(page.offset);
      setStatus("ready");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Erro inesperado.");
      setStatus("error");
    }
  }

  useEffect(() => {
    let active = true;
    fetch(`/api/projects?offset=0&limit=${PAGE_SIZE}`, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error("Não foi possível carregar os projetos.");
        return response.json() as Promise<ProjectPage>;
      })
      .then((page) => {
        if (!active) return;
        setProjects(page.items);
        setTotal(page.total);
        setOffset(page.offset);
        setStatus("ready");
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setMessage(reason instanceof Error ? reason.message : "Erro inesperado.");
        setStatus("error");
      });
    return () => { active = false; };
  }, []);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await projectRequest("/api/projects", "POST", csrfToken, {
      name: form.get("name"),
      description: form.get("description"),
    });
    if (!response.ok) return setMessage(await responseMessage(response));
    formElement.reset();
    await loadProjects(0);
    setMessage("Projeto criado com sucesso.");
  }

  async function updateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const form = new FormData(event.currentTarget);
    const response = await projectRequest(`/api/projects/${editing.id}`, "PATCH", csrfToken, {
      name: form.get("name"),
      description: form.get("description"),
      version: editing.version,
    });
    if (!response.ok) return setMessage(await responseMessage(response));
    setEditing(null);
    await loadProjects(offset);
    setMessage("Projeto atualizado com sucesso.");
  }

  async function archiveProject(project: Project) {
    if (!window.confirm(`Arquivar o projeto “${project.name}”? O histórico será preservado.`)) return;
    const response = await projectRequest(
      `/api/projects/${project.id}/archive`,
      "POST",
      csrfToken,
    );
    if (!response.ok) return setMessage(await responseMessage(response));
    await loadProjects(offset);
    setMessage("Projeto arquivado. O histórico foi preservado.");
  }

  return (
    <div className="workspace">
      <header className="app-header">
        <div>
          <p className="eyebrow">Ambiente local · {user.role}</p>
          <h1>Projetos</h1>
          <p className="welcome">Olá, {user.name}. Selecione um projeto para organizar os testes.</p>
        </div>
        <div className="header-actions">
          {user.role === "ADMIN" && <button type="button" className="secondary" onClick={onUsers}>Utilizadores</button>}
          <button type="button" className="secondary" onClick={onLogout}>Terminar sessão</button>
        </div>
      </header>

      {user.role === "ADMIN" && (
        <section className="panel" aria-labelledby="new-project-title">
          <h2 id="new-project-title">Novo projeto</h2>
          <form className="project-form" onSubmit={createProject}>
            <label htmlFor="project-name">Nome</label>
            <input id="project-name" name="name" minLength={2} maxLength={160} required />
            <label htmlFor="project-description">Descrição</label>
            <textarea id="project-description" name="description" maxLength={4000} rows={3} />
            <button type="submit">Criar projeto</button>
          </form>
        </section>
      )}

      <section className="panel" aria-labelledby="project-list-title">
        <div className="section-heading">
          <div><h2 id="project-list-title">Projetos ativos</h2><p>{total} projeto(s)</p></div>
          <button type="button" className="tertiary" onClick={() => loadProjects(offset)}>Atualizar</button>
        </div>
        {message && <p className={status === "error" ? "error" : "notice"} role="status">{message}</p>}
        {status === "loading" && <p className="empty-state">A carregar projetos…</p>}
        {status === "error" && <button type="button" onClick={() => loadProjects(offset)}>Tentar novamente</button>}
        {status === "ready" && projects.length === 0 && (
          <p className="empty-state">Ainda não existem projetos ativos.</p>
        )}
        {status === "ready" && projects.length > 0 && (
          <div className="project-grid">
            {projects.map((project) => (
              <article className="project-card" key={project.id}>
                <div><h3>{project.name}</h3><p>{project.description || "Sem descrição."}</p></div>
                {user.role === "ADMIN" && <div className="card-actions">
                  <button type="button" className="tertiary" onClick={() => setEditing(project)}>Editar</button>
                  <button type="button" className="danger" onClick={() => archiveProject(project)}>Arquivar</button>
                </div>}
              </article>
            ))}
          </div>
        )}
        {total > PAGE_SIZE && <nav className="pagination" aria-label="Paginação de projetos">
          <button type="button" className="tertiary" disabled={offset === 0} onClick={() => loadProjects(Math.max(0, offset - PAGE_SIZE))}>Anterior</button>
          <span>Página {Math.floor(offset / PAGE_SIZE) + 1}</span>
          <button type="button" className="tertiary" disabled={offset + PAGE_SIZE >= total} onClick={() => loadProjects(offset + PAGE_SIZE)}>Seguinte</button>
        </nav>}
      </section>

      {editing && <div className="dialog-backdrop" role="presentation">
        <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="edit-project-title">
          <h2 id="edit-project-title">Editar projeto</h2>
          <form className="project-form" onSubmit={updateProject}>
            <label htmlFor="edit-project-name">Nome</label>
            <input id="edit-project-name" name="name" defaultValue={editing.name} minLength={2} maxLength={160} required autoFocus />
            <label htmlFor="edit-project-description">Descrição</label>
            <textarea id="edit-project-description" name="description" defaultValue={editing.description} maxLength={4000} rows={4} />
            <div className="dialog-actions"><button type="button" className="secondary" onClick={() => setEditing(null)}>Cancelar</button><button type="submit">Guardar</button></div>
          </form>
        </section>
      </div>}
    </div>
  );
}

async function projectRequest(url: string, method: string, csrfToken: string, body?: object) {
  return fetch(url, {
    method,
    credentials: "include",
    headers: { "X-CSRF-Token": csrfToken, ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function responseMessage(response: Response) {
  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  return payload?.detail || "Não foi possível concluir a operação.";
}
