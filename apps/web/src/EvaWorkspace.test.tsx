import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { EvaWorkspace } from "./EvaWorkspace";

const admin = { id: 1, name: "Admin", email: "admin@example.com", role: "ADMIN" as const };
const project = { id: 1, name: "Portal", description: "", is_archived: false, version: 1 };

describe("EvaWorkspace", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("prepares a package and exposes both downloads", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ public_id: "abc", json_url: "/eva/exchanges/abc/request.json", markdown_url: "/eva/exchanges/abc/request.md" }, 201));
    render(<EvaWorkspace user={admin} project={project} csrfToken="csrf" onCases={vi.fn()} onBack={vi.fn()} onLogout={vi.fn()} />);
    await screen.findByText("Ainda não existem propostas importadas.");
    fireEvent.change(screen.getByLabelText("Título"), { target: { value: "Login" } });
    fireEvent.change(screen.getByLabelText("Requisito ou contexto"), { target: { value: "O utilizador deve entrar." } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar pacote" }));

    await waitFor(() => expect(screen.getByRole("link", { name: "Download JSON" })).toHaveAttribute("href", "/api/eva/exchanges/abc/request.json"));
    expect(screen.getByRole("link", { name: "Download Markdown" })).toHaveAttribute("href", "/api/eva/exchanges/abc/request.md");
  });

  it("shows proposals and prevents approving a duplicate", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse([{ id: 1, proposal_key: "login", category: "POSITIVE", status: "DRAFT", payload: { title: "Login válido", requirement: "RF", description: "Validar login", expected_result: "Sessão" }, converted_test_case_id: null, duplicate: true }]));
    render(<EvaWorkspace user={admin} project={project} csrfToken="csrf" onCases={vi.fn()} onBack={vi.fn()} onLogout={vi.fn()} />);

    await screen.findByText("Login válido");
    expect(screen.getByRole("button", { name: "Aprovar" })).toBeDisabled();
    expect(screen.getByText(/Possível duplicado/)).not.toBeNull();
  });
});

function jsonResponse(value: object, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}
