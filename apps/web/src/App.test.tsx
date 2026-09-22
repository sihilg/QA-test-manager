import { render, screen } from "@testing-library/react";

import { App } from "./App";

describe("App", () => {
  it("identifies the local product foundation", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "QA Test Manager" })).not.toBeNull();
    expect(screen.getByRole("status").textContent).toContain("Fundação técnica pronta");
  });
});
