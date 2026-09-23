import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { Projects } from "./Projects";

const admin = { id: 1, name: "Admin", email: "admin@example.com", role: "ADMIN" as const };
const emptyPage = { items: [], total: 0, offset: 0, limit: 10 };

describe("Projects", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows the empty state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(emptyPage), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<Projects user={admin} csrfToken="csrf" onLogout={vi.fn()} onUsers={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("Ainda não existem projetos ativos.")).not.toBeNull());
  });

  it("creates a project and reloads the list", async () => {
    const project = {
      id: 1,
      name: "Portal QA",
      description: "Testes do portal",
      is_archived: false,
      version: 1,
    };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(emptyPage))
      .mockResolvedValueOnce(jsonResponse(project, 201))
      .mockResolvedValueOnce(jsonResponse({ ...emptyPage, items: [project], total: 1 }));
    render(<Projects user={admin} csrfToken="csrf" onLogout={vi.fn()} onUsers={vi.fn()} />);
    await screen.findByText("Ainda não existem projetos ativos.");

    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Portal QA" } });
    fireEvent.change(screen.getByLabelText("Descrição"), { target: { value: "Testes do portal" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar projeto" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Portal QA" })).not.toBeNull());
    expect(screen.getByText("Projeto criado com sucesso.")).not.toBeNull();
  });
});

function jsonResponse(value: object, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
