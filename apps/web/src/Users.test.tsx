import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { Users } from "./Users";

const admin = { id: 1, name: "Admin", email: "admin@example.com", role: "ADMIN" as const };
const adminRecord = { ...admin, is_active: true, version: 1 };

describe("Users", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("lists users without exposing password hashes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ items: [adminRecord], total: 1, offset: 0, limit: 20 }));
    render(<Users currentUser={admin} csrfToken="csrf" onProjects={vi.fn()} onLogout={vi.fn()} />);

    await waitFor(() => expect(screen.getByText("admin@example.com")).not.toBeNull());
    expect(screen.queryByText(/password_hash/i)).toBeNull();
    expect(screen.getByText("Você")).not.toBeNull();
  });

  it("creates a tester and refreshes the list", async () => {
    const tester = { id: 2, name: "Tester", email: "tester@example.com", role: "TESTER", is_active: true, version: 1 };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ items: [adminRecord], total: 1, offset: 0, limit: 20 }))
      .mockResolvedValueOnce(jsonResponse(tester, 201))
      .mockResolvedValueOnce(jsonResponse({ items: [adminRecord, tester], total: 2, offset: 0, limit: 20 }));
    render(<Users currentUser={admin} csrfToken="csrf" onProjects={vi.fn()} onLogout={vi.fn()} />);
    await screen.findByText("admin@example.com");

    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Tester" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "tester@example.com" } });
    fireEvent.change(screen.getByLabelText("Palavra-passe inicial"), { target: { value: "tester-password-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar utilizador" }));

    await waitFor(() => expect(screen.getByText("tester@example.com")).not.toBeNull());
    expect(screen.getByText("Utilizador criado com sucesso.")).not.toBeNull();
  });

  it("shows a duplicate email error next to the creation form", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ items: [adminRecord], total: 1, offset: 0, limit: 20 }))
      .mockResolvedValueOnce(jsonResponse({ detail: "Já existe um utilizador com este email." }, 409));
    render(<Users currentUser={admin} csrfToken="csrf" onProjects={vi.fn()} onLogout={vi.fn()} />);
    await screen.findByText("admin@example.com");

    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Outro Admin" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@example.com" } });
    fireEvent.change(screen.getByLabelText("Palavra-passe inicial"), { target: { value: "another-password-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar utilizador" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Já existe um utilizador com este email.");
  });
});

function jsonResponse(value: object, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}
