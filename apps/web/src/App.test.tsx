import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { App } from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 401 }));
  });

  it("shows the local login form", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "QA Test Manager" })).not.toBeNull();
    expect(screen.getByLabelText("Email")).not.toBeNull();
    expect(screen.getByLabelText("Palavra-passe")).not.toBeNull();
  });

  it("temporarily reveals and hides the password", () => {
    render(<App />);
    const password = screen.getByLabelText("Palavra-passe") as HTMLInputElement;

    expect(password.type).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: "Mostrar palavra-passe" }));
    expect(password.type).toBe("text");
    fireEvent.click(screen.getByRole("button", { name: "Ocultar palavra-passe" }));
    expect(password.type).toBe("password");
  });

  it("shows the authenticated user after login", async () => {
    vi.mocked(globalThis.fetch)
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(
        JSON.stringify({
          user: { id: 1, name: "Admin Local", email: "admin@example.com", role: "ADMIN" },
          csrf_token: "csrf",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@example.com" } });
    fireEvent.change(screen.getByLabelText("Palavra-passe"), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => expect(screen.getByText("Olá, Admin Local. Selecione um projeto para organizar os testes.")).not.toBeNull());
  });
});
