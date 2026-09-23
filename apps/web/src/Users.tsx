import { FormEvent, useEffect, useState } from "react";

type User = {
  id: number;
  name: string;
  email: string;
  role: "ADMIN" | "TESTER" | "DEV";
  is_active?: boolean;
  version?: number;
};
type ManagedUser = Required<User>;
type UserPage = { items: ManagedUser[]; total: number; offset: number; limit: number };

export function Users({ currentUser, csrfToken, onProjects, onLogout }: { currentUser: User; csrfToken: string; onProjects: () => void; onLogout: () => void }) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [formMessage, setFormMessage] = useState("");
  const [editing, setEditing] = useState<ManagedUser | null>(null);
  const [showCreatePassword, setShowCreatePassword] = useState(false);

  async function loadUsers() {
    setStatus("loading");
    setMessage("");
    try {
      const response = await fetch("/api/users", {
        credentials: "include",
        headers: { "X-CSRF-Token": csrfToken },
      });
      if (!response.ok) throw new Error(await responseMessage(response));
      const page = (await response.json()) as UserPage;
      setUsers(page.items);
      setStatus("ready");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Erro inesperado.");
      setStatus("error");
    }
  }

  useEffect(() => {
    let active = true;
    fetch("/api/users", { credentials: "include", headers: { "X-CSRF-Token": csrfToken } })
      .then(async (response) => {
        if (!response.ok) throw new Error(await responseMessage(response));
        return response.json() as Promise<UserPage>;
      })
      .then((page) => { if (active) { setUsers(page.items); setStatus("ready"); } })
      .catch((reason: unknown) => { if (active) { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setStatus("error"); } });
    return () => { active = false; };
  }, [csrfToken]);

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await userRequest("/api/users", "POST", csrfToken, {
      name: form.get("name"), email: form.get("email"), password: form.get("password"), role: form.get("role"),
    });
    if (!response.ok) return setFormMessage(await responseMessage(response));
    formElement.reset();
    await loadUsers();
    setFormMessage("Utilizador criado com sucesso.");
  }

  async function updateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    const body: Record<string, unknown> = {
      name: form.get("name"), email: form.get("email"), role: form.get("role"), version: editing.version,
    };
    if (password) body.password = password;
    const response = await userRequest(`/api/users/${editing.id}`, "PATCH", csrfToken, body);
    if (!response.ok) return setMessage(await responseMessage(response));
    setEditing(null);
    await loadUsers();
    setMessage("Utilizador atualizado com sucesso.");
  }

  async function toggleActive(user: ManagedUser) {
    const action = user.is_active ? "deactivate" : "activate";
    const verb = user.is_active ? "desativar" : "ativar";
    if (!window.confirm(`Deseja ${verb} ${user.name}?`)) return;
    const response = await userRequest(`/api/users/${user.id}/${action}`, "POST", csrfToken);
    if (!response.ok) return setMessage(await responseMessage(response));
    await loadUsers();
    setMessage(`Utilizador ${user.is_active ? "desativado" : "ativado"} com sucesso.`);
  }

  return <div className="workspace">
    <header className="app-header">
      <div><p className="eyebrow">Backoffice · acesso Admin</p><h1>Utilizadores</h1><p className="welcome">Gerencie os acessos desta instalação local.</p></div>
      <div className="header-actions"><button type="button" className="secondary" onClick={onProjects}>Projetos</button><button type="button" className="secondary" onClick={onLogout}>Terminar sessão</button></div>
    </header>

    <section className="panel" aria-labelledby="new-user-title">
      <h2 id="new-user-title">Novo utilizador</h2>
      <form className="project-form" onSubmit={createUser}>
        <label htmlFor="user-name">Nome</label><input id="user-name" name="name" minLength={2} maxLength={120} required />
        <label htmlFor="user-email">Email</label><input id="user-email" name="email" type="email" aria-describedby="user-email-help" required /><small id="user-email-help" className="field-help">Use um email diferente para cada utilizador. Este será o identificador de login.</small>
        <label htmlFor="user-role">Perfil</label><select id="user-role" name="role" defaultValue="TESTER"><option value="ADMIN">Admin</option><option value="TESTER">Tester</option><option value="DEV">Dev</option></select>
        <label htmlFor="user-password">Palavra-passe inicial</label>
        <div className="password-field"><input id="user-password" name="password" type={showCreatePassword ? "text" : "password"} minLength={12} required /><button type="button" className="password-toggle text-toggle" onClick={() => setShowCreatePassword((value) => !value)} aria-label={showCreatePassword ? "Ocultar palavra-passe inicial" : "Mostrar palavra-passe inicial"}>{showCreatePassword ? "Ocultar" : "Mostrar"}</button></div>
        {formMessage && <p className={formMessage.includes("sucesso") ? "notice" : "error"} role="alert">{formMessage}</p>}
        <button type="submit">Criar utilizador</button>
      </form>
    </section>

    <section className="panel" aria-labelledby="user-list-title">
      <div className="section-heading"><div><h2 id="user-list-title">Utilizadores</h2><p>{users.length} utilizador(es)</p></div><button type="button" className="tertiary" onClick={loadUsers}>Atualizar</button></div>
      {message && <p className={status === "error" ? "error" : "notice"} role="status">{message}</p>}
      {status === "loading" && <p className="empty-state">A carregar utilizadores…</p>}
      {status === "error" && <button type="button" onClick={loadUsers}>Tentar novamente</button>}
      {status === "ready" && <div className="user-table-wrapper"><table><thead><tr><th>Nome</th><th>Email</th><th>Perfil</th><th>Estado</th><th>Ações</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.name}{user.id === currentUser.id && <span className="you-badge">Você</span>}</td><td>{user.email}</td><td>{user.role}</td><td><span className={user.is_active ? "active-badge" : "inactive-badge"}>{user.is_active ? "Ativo" : "Inativo"}</span></td><td><div className="card-actions"><button type="button" className="tertiary" onClick={() => setEditing(user)}>Editar</button><button type="button" className={user.is_active ? "danger" : "tertiary"} onClick={() => toggleActive(user)}>{user.is_active ? "Desativar" : "Ativar"}</button></div></td></tr>)}</tbody></table></div>}
    </section>

    {editing && <div className="dialog-backdrop" role="presentation"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="edit-user-title"><h2 id="edit-user-title">Editar utilizador</h2><form className="project-form" onSubmit={updateUser}><label htmlFor="edit-user-name">Nome</label><input id="edit-user-name" name="name" defaultValue={editing.name} minLength={2} maxLength={120} required autoFocus /><label htmlFor="edit-user-email">Email</label><input id="edit-user-email" name="email" type="email" defaultValue={editing.email} required /><label htmlFor="edit-user-role">Perfil</label><select id="edit-user-role" name="role" defaultValue={editing.role}><option value="ADMIN">Admin</option><option value="TESTER">Tester</option><option value="DEV">Dev</option></select><label htmlFor="edit-user-password">Nova palavra-passe (opcional)</label><input id="edit-user-password" name="password" type="password" minLength={12} /><div className="dialog-actions"><button type="button" className="secondary" onClick={() => setEditing(null)}>Cancelar</button><button type="submit">Guardar</button></div></form></section></div>}
  </div>;
}

async function userRequest(url: string, method: string, csrfToken: string, body?: object) {
  return fetch(url, { method, credentials: "include", headers: { "X-CSRF-Token": csrfToken, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
}

async function responseMessage(response: Response) {
  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  return payload?.detail || "Não foi possível concluir a operação.";
}
