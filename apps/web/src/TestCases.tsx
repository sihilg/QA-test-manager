import { FormEvent, useEffect, useState } from "react";

import type { Project } from "./Projects";

type User = { id: number; name: string; email: string; role: "ADMIN" | "TESTER" | "DEV" };
type Step = { id?: number; position: number; action: string; expected_result: string | null };
type TestCase = {
  id: number; project_id: number; case_number: string; execution_order: number;
  priority: "HIGH" | "MEDIUM" | "LOW"; executor_id: number | null; execution_date: string | null;
  requirement: string; browser: string | null; test_type: "FUNCTIONAL_POSITIVE" | "FUNCTIONAL_NEGATIVE" | "BLACK_BOX" | "BOUNDARY_VALUE_ANALYSIS";
  title: string; test_data: string; description: string; preconditions: string; expected_result: string;
  final_result: "NOT_EXECUTED" | "PASSED" | "FAILED" | "BLOCKED"; origin: "MANUAL" | "EVA" | "AUTOMATION_TOOL";
  version: number; steps: Step[];
};
type CaseItem = Pick<TestCase, "id" | "case_number" | "title" | "priority" | "test_type" | "final_result" | "version">;
type CasePage = { items: CaseItem[]; total: number };

export function TestCases({ user, project, csrfToken, onBack, onLogout }: { user: User; project: Project; csrfToken: string; onBack: () => void; onLogout: () => void }) {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [filters, setFilters] = useState({ result: "", priority: "", test_type: "" });
  const [formCase, setFormCase] = useState<TestCase | null | "new">(null);

  async function loadCases(nextFilters = filters, announce = false) {
    setStatus("loading"); setMessage("");
    const params = new URLSearchParams();
    Object.entries(nextFilters).forEach(([key, value]) => { if (value) params.set(key, value); });
    try {
      const response = await fetch(`/api/projects/${project.id}/test-cases?${params}`, { credentials: "include" });
      if (!response.ok) throw new Error("Não foi possível carregar os casos.");
      const page = (await response.json()) as CasePage;
      setCases(page.items); setStatus("ready");
      if (announce) setMessage(`Filtros aplicados: ${page.total} caso(s) encontrado(s).`);
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setStatus("error"); }
  }

  useEffect(() => {
    let active = true;
    fetch(`/api/projects/${project.id}/test-cases`, { credentials: "include" })
      .then((response) => { if (!response.ok) throw new Error("Não foi possível carregar os casos."); return response.json() as Promise<CasePage>; })
      .then((page) => { if (active) { setCases(page.items); setStatus("ready"); } })
      .catch((reason: unknown) => { if (active) { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setStatus("error"); } });
    return () => { active = false; };
  }, [project.id]);

  async function openCase(item: CaseItem) {
    const response = await fetch(`/api/test-cases/${item.id}`, { credentials: "include" });
    if (!response.ok) return setMessage("Não foi possível abrir o caso.");
    setFormCase((await response.json()) as TestCase);
  }

  async function saveCase(payload: Record<string, unknown>): Promise<string | null> {
    const editing = formCase !== "new" && formCase !== null ? formCase : null;
    const url = editing ? `/api/test-cases/${editing.id}` : `/api/projects/${project.id}/test-cases`;
    const response = await apiRequest(url, editing ? "PUT" : "POST", csrfToken, editing ? { ...payload, version: editing.version } : payload);
    if (!response.ok) return responseMessage(response);
    setFormCase(null); await loadCases(); setMessage(editing ? "Caso atualizado com sucesso." : "Caso criado com sucesso.");
    return null;
  }

  async function archiveCase(testCase: TestCase) {
    if (!window.confirm(`Arquivar ${testCase.case_number}? O histórico será preservado.`)) return;
    const response = await apiRequest(`/api/test-cases/${testCase.id}/archive`, "POST", csrfToken);
    if (!response.ok) return setMessage(await responseMessage(response));
    setFormCase(null); await loadCases(); setMessage("Caso arquivado. O número não será reutilizado.");
  }

  const canEdit = user.role !== "DEV";
  return <div className="workspace">
    <header className="app-header"><div><p className="eyebrow">Projeto · {project.name}</p><h1>Casos de teste</h1><p className="welcome">Crie casos manuais reproduzíveis e acompanhe o resultado.</p></div><div className="header-actions"><button type="button" className="secondary" onClick={onBack}>Projetos</button><button type="button" className="secondary" onClick={onLogout}>Terminar sessão</button></div></header>

    <section className="panel filters" aria-label="Filtros"><select aria-label="Filtrar por resultado" value={filters.result} onChange={(event) => setFilters({ ...filters, result: event.target.value })}><option value="">Todos os resultados</option><option value="NOT_EXECUTED">Não executado</option><option value="PASSED">Passed</option><option value="FAILED">Failed</option><option value="BLOCKED">Blocked</option></select><select aria-label="Filtrar por prioridade" value={filters.priority} onChange={(event) => setFilters({ ...filters, priority: event.target.value })}><option value="">Todas as prioridades</option><option value="HIGH">Alta</option><option value="MEDIUM">Média</option><option value="LOW">Baixa</option></select><select aria-label="Filtrar por tipo" value={filters.test_type} onChange={(event) => setFilters({ ...filters, test_type: event.target.value })}><option value="">Todos os tipos</option><option value="FUNCTIONAL_POSITIVE">Functional Positive</option><option value="FUNCTIONAL_NEGATIVE">Functional Negative</option><option value="BLACK_BOX">Black Box</option><option value="BOUNDARY_VALUE_ANALYSIS">BVA</option></select><button type="button" disabled={status === "loading"} onClick={() => loadCases(filters, true)}>{status === "loading" ? "A aplicar…" : "Aplicar filtros"}</button><button type="button" className="tertiary" disabled={status === "loading"} onClick={() => { const cleared = { result: "", priority: "", test_type: "" }; setFilters(cleared); void loadCases(cleared, true); }}>Limpar filtros</button>{canEdit && <button type="button" onClick={() => setFormCase("new")}>Novo caso</button>}</section>

    <section className="panel export-panel" aria-label="Exportar lista filtrada"><strong>Exportar lista filtrada</strong>{(["docx", "xlsx", "pdf"] as const).map((format) => <a className="export-link" key={format} href={projectExportUrl(project.id, format, filters)}>{format.toUpperCase()}</a>)}</section>

    <section className="panel" aria-labelledby="case-list-title"><div className="section-heading"><div><h2 id="case-list-title">Casos ativos</h2><p>{cases.length} caso(s)</p></div><button type="button" className="tertiary" onClick={() => loadCases()}>Atualizar</button></div>{message && <p className={status === "error" ? "error" : "notice"} role="status">{message}</p>}{status === "loading" && <p className="empty-state">A carregar casos…</p>}{status === "error" && <button type="button" onClick={() => loadCases()}>Tentar novamente</button>}{status === "ready" && cases.length === 0 && <p className="empty-state">Ainda não existem casos para este projeto.</p>}{status === "ready" && cases.length > 0 && <div className="case-list">{cases.map((item) => <div className="case-row-with-exports" key={item.id}><button type="button" className="case-row" onClick={() => openCase(item)}><strong>{item.case_number}</strong><span>{item.title}</span><span className={`result-badge ${item.final_result.toLowerCase()}`}>{item.final_result}</span></button><div className="case-export-links" aria-label={`Exportar ${item.case_number}`}>{(["docx", "xlsx", "pdf"] as const).map((format) => <a key={format} href={`/api/test-cases/${item.id}/export/${format}`} aria-label={`Exportar ${item.case_number} em ${format.toUpperCase()}`}>{format.toUpperCase()}</a>)}</div></div>)}</div>}</section>

    {formCase && <CaseDialog testCase={formCase === "new" ? null : formCase} canEdit={canEdit} onSave={saveCase} onArchive={archiveCase} onClose={() => setFormCase(null)} />}
  </div>;
}

function CaseDialog({ testCase, canEdit, onSave, onArchive, onClose }: { testCase: TestCase | null; canEdit: boolean; onSave: (payload: Record<string, unknown>) => Promise<string | null>; onArchive: (testCase: TestCase) => Promise<void>; onClose: () => void }) {
  const [steps, setSteps] = useState<Step[]>(testCase?.steps || [{ position: 1, action: "", expected_result: "" }]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try {
      const error = await onSave({ execution_order: Number(form.get("execution_order")), priority: form.get("priority"), execution_date: form.get("execution_date") || null, requirement: form.get("requirement"), browser: form.get("browser") || null, test_type: form.get("test_type"), title: form.get("title"), test_data: form.get("test_data"), description: form.get("description"), preconditions: form.get("preconditions"), expected_result: form.get("expected_result"), final_result: form.get("final_result"), origin: "MANUAL", executor_id: null, steps: steps.map((step, index) => ({ position: index + 1, action: step.action, expected_result: step.expected_result || null })) });
      if (error) window.alert(error);
    } catch { window.alert("Não foi possível guardar o caso. Tente novamente."); }
  }
  function updateStep(index: number, field: "action" | "expected_result", value: string) { setSteps(steps.map((step, current) => current === index ? { ...step, [field]: value } : step)); }
  return <div className="dialog-backdrop"><section className="dialog case-dialog" role="dialog" aria-modal="true" aria-labelledby="case-form-title"><div className="section-heading"><h2 id="case-form-title">{testCase ? `${testCase.case_number} · Editar caso` : "Novo caso manual"}</h2><button type="button" className="tertiary" onClick={onClose}>Fechar</button></div><form className="case-form" onSubmit={submit}><label>Ordem<input name="execution_order" type="number" min="1" defaultValue={testCase?.execution_order || 1} disabled={!canEdit} required /></label><label>Prioridade<select name="priority" defaultValue={testCase?.priority || "MEDIUM"} disabled={!canEdit}><option value="HIGH">Alta</option><option value="MEDIUM">Média</option><option value="LOW">Baixa</option></select></label><label>Tipo<select name="test_type" defaultValue={testCase?.test_type || "FUNCTIONAL_POSITIVE"} disabled={!canEdit}><option value="FUNCTIONAL_POSITIVE">Functional Positive</option><option value="FUNCTIONAL_NEGATIVE">Functional Negative</option><option value="BLACK_BOX">Black Box</option><option value="BOUNDARY_VALUE_ANALYSIS">BVA</option></select></label><label>Resultado<select name="final_result" defaultValue={testCase?.final_result || "NOT_EXECUTED"} disabled={!canEdit}><option value="NOT_EXECUTED">Não executado</option><option value="PASSED">Passed</option><option value="FAILED">Failed</option><option value="BLOCKED">Blocked</option></select></label><label className="span-2">Título<input name="title" defaultValue={testCase?.title} minLength={2} maxLength={240} disabled={!canEdit} required /></label><label>Requisito<input name="requirement" defaultValue={testCase?.requirement} disabled={!canEdit} required /></label><label>Browser<input name="browser" defaultValue={testCase?.browser || ""} disabled={!canEdit} /></label><label>Data de execução<input name="execution_date" type="date" defaultValue={testCase?.execution_date || ""} disabled={!canEdit} /></label><label className="span-2">Dados de teste<textarea name="test_data" defaultValue={testCase?.test_data} disabled={!canEdit} required /></label><label className="span-2">Descrição<textarea name="description" defaultValue={testCase?.description} disabled={!canEdit} required /></label><label className="span-2">Pré-condições<textarea name="preconditions" defaultValue={testCase?.preconditions} disabled={!canEdit} required /></label><label className="span-2">Resultado esperado<textarea name="expected_result" defaultValue={testCase?.expected_result} disabled={!canEdit} required /></label><fieldset className="span-2"><legend>Passos</legend>{steps.map((step, index) => <div className="step-row" key={index}><span>{index + 1}</span><input aria-label={`Ação do passo ${index + 1}`} value={step.action} onChange={(event) => updateStep(index, "action", event.target.value)} disabled={!canEdit} required /><input aria-label={`Resultado do passo ${index + 1}`} value={step.expected_result || ""} onChange={(event) => updateStep(index, "expected_result", event.target.value)} disabled={!canEdit} placeholder="Resultado esperado do passo" />{canEdit && steps.length > 1 && <button type="button" className="danger" onClick={() => setSteps(steps.filter((_, current) => current !== index))}>Remover</button>}</div>)}{canEdit && <button type="button" className="tertiary" onClick={() => setSteps([...steps, { position: steps.length + 1, action: "", expected_result: "" }])}>Adicionar passo</button>}</fieldset>{canEdit && <div className="dialog-actions span-2">{testCase && <button type="button" className="danger" onClick={() => onArchive(testCase)}>Arquivar</button>}<button type="submit">Guardar caso</button></div>}</form></section></div>;
}

async function apiRequest(url: string, method: string, csrfToken: string, body?: object) { return fetch(url, { method, credentials: "include", headers: { "X-CSRF-Token": csrfToken, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined }); }
async function responseMessage(response: Response) { const payload = (await response.json().catch(() => null)) as { detail?: string } | null; return typeof payload?.detail === "string" ? payload.detail : "Não foi possível concluir a operação."; }
function projectExportUrl(projectId: number, format: "docx" | "xlsx" | "pdf", filters: { result: string; priority: string; test_type: string }) { const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); }); const query = params.toString(); return `/api/projects/${projectId}/test-cases/export/${format}${query ? `?${query}` : ""}`; }
