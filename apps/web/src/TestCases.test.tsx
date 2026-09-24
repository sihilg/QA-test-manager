import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { TestCases } from "./TestCases";

const admin = { id: 1, name: "Admin", email: "admin@example.com", role: "ADMIN" as const };
const project = { id: 1, name: "Portal", description: "", is_archived: false, version: 1 };
const emptyPage = { items: [], total: 0 };

describe("TestCases", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows an empty state for a project without cases", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(emptyPage));
    render(<TestCases user={admin} project={project} csrfToken="csrf" onBack={vi.fn()} onLogout={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("Ainda não existem casos para este projeto.")).not.toBeNull());
  });

  it("applies the selected filters and confirms the result", async () => {
    const fetch = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(emptyPage))
      .mockResolvedValueOnce(jsonResponse(emptyPage));
    render(<TestCases user={admin} project={project} csrfToken="csrf" onBack={vi.fn()} onLogout={vi.fn()} />);
    await screen.findByText("Ainda não existem casos para este projeto.");

    fireEvent.change(screen.getByLabelText("Filtrar por prioridade"), { target: { value: "HIGH" } });
    fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await screen.findByText("Filtros aplicados: 0 caso(s) encontrado(s).");
    expect(fetch.mock.calls[1][0]).toBe("/api/projects/1/test-cases?priority=HIGH");
  });

  it("creates a manual case and shows its immutable number", async () => {
    const item = { id: 1, case_number: "CT001", title: "Login válido", priority: "HIGH", test_type: "FUNCTIONAL_POSITIVE", final_result: "NOT_EXECUTED", version: 1 };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(emptyPage))
      .mockResolvedValueOnce(jsonResponse({ ...item, project_id: 1, execution_order: 1, executor_id: null, execution_date: null, requirement: "RF-001", browser: null, test_data: "Dados", description: "Descrição", preconditions: "Admin ativo", expected_result: "Sessão iniciada", origin: "MANUAL", is_archived: false, steps: [{ id: 1, position: 1, action: "Entrar", expected_result: "Sessão" }], created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }, 201))
      .mockResolvedValueOnce(jsonResponse({ items: [item], total: 1 }));
    render(<TestCases user={admin} project={project} csrfToken="csrf" onBack={vi.fn()} onLogout={vi.fn()} />);
    await screen.findByText("Ainda não existem casos para este projeto.");
    fireEvent.click(screen.getByRole("button", { name: "Novo caso" }));

    fill("Título", "Login válido"); fill("Requisito", "RF-001"); fill("Dados de teste", "Dados fictícios");
    fill("Descrição", "Validar login"); fill("Pré-condições", "Admin ativo"); fill("Resultado esperado", "Sessão iniciada");
    fireEvent.change(screen.getByLabelText("Ação do passo 1"), { target: { value: "Enviar credenciais" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar caso" }));

    await waitFor(() => expect(screen.getByText("CT001")).not.toBeNull());
    expect(screen.getByText("Caso criado com sucesso.")).not.toBeNull();
  });

  it("shows the server error when a case cannot be saved", async () => {
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(emptyPage))
      .mockResolvedValueOnce(jsonResponse({ detail: "A ordem de execução já está em uso neste projeto." }, 409));
    render(<TestCases user={admin} project={project} csrfToken="csrf" onBack={vi.fn()} onLogout={vi.fn()} />);
    await screen.findByText("Ainda não existem casos para este projeto.");
    fireEvent.click(screen.getByRole("button", { name: "Novo caso" }));

    fill("Título", "Login alternativo"); fill("Requisito", "RF-002"); fill("Dados de teste", "Dados fictícios");
    fill("Descrição", "Validar login alternativo"); fill("Pré-condições", "Utilizador ativo"); fill("Resultado esperado", "Sessão iniciada");
    fireEvent.change(screen.getByLabelText("Ação do passo 1"), { target: { value: "Enviar credenciais" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar caso" }));

    await waitFor(() => expect(alert).toHaveBeenCalledWith("A ordem de execução já está em uso neste projeto."));
    expect(screen.getByRole("dialog")).not.toBeNull();
  });
});

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function jsonResponse(value: object, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}
