// Milestone 27 · Increment 2 (SESSION_193) — GLAccountPicker tests.
//
// Asserts the M27.0 §5.b user-directed contract: the picker is
// searchable by BOTH account code AND account name; selection fires
// the onChange callback with the picked id; clearing the selection
// puts the search box back into view.

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GLAccountPicker } from "@/components/accounting/GLAccountPicker";
import type { GLAccount } from "@/lib/accountingApi";


function makeAccounts(): GLAccount[] {
  return [
    { id: 1, code: "110000", name: "Bank — Operating", type: "asset" },
    { id: 2, code: "120000", name: "Accounts Receivable", type: "asset" },
    { id: 3, code: "400000", name: "Vehicle Sales — Retail", type: "revenue" },
    { id: 4, code: "500000", name: "Cost of Sales", type: "expense" },
  ];
}


describe("GLAccountPicker", () => {
  it("renders all accounts when no query is set", () => {
    const onChange = vi.fn();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={null}
        onChange={onChange}
      />,
    );
    expect(screen.getByTestId("gl-account-option-110000")).toBeInTheDocument();
    expect(screen.getByTestId("gl-account-option-400000")).toBeInTheDocument();
    expect(screen.getByTestId("gl-account-option-500000")).toBeInTheDocument();
  });

  it("filters by account code", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={null}
        onChange={onChange}
      />,
    );
    await user.type(screen.getByRole("searchbox"), "110");
    expect(
      screen.getByTestId("gl-account-option-110000"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("gl-account-option-400000"),
    ).not.toBeInTheDocument();
  });

  it("filters by account name", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={null}
        onChange={onChange}
      />,
    );
    await user.type(screen.getByRole("searchbox"), "sales");
    // Vehicle Sales — Retail (400000) and Cost of Sales (500000) both
    // match on the name; Bank + AR do not.
    expect(
      screen.getByTestId("gl-account-option-400000"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("gl-account-option-500000"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("gl-account-option-110000"),
    ).not.toBeInTheDocument();
  });

  it("filters case-insensitively", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={null}
        onChange={onChange}
      />,
    );
    await user.type(screen.getByRole("searchbox"), "BANK");
    expect(
      screen.getByTestId("gl-account-option-110000"),
    ).toBeInTheDocument();
  });

  it("shows an empty-state message when no accounts match", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={null}
        onChange={onChange}
      />,
    );
    await user.type(screen.getByRole("searchbox"), "zzzz");
    expect(screen.getByText(/No accounts match/i)).toBeInTheDocument();
  });

  it("fires onChange with the picked id when an option is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={null}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByTestId("gl-account-option-400000"));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("shows the selected account instead of the search box when value is set", () => {
    const onChange = vi.fn();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={3}
        onChange={onChange}
      />,
    );
    const selected = screen.getByTestId("gl-account-picker-selected");
    expect(selected).toHaveTextContent("400000");
    expect(selected).toHaveTextContent("Vehicle Sales — Retail");
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
  });

  it("clears the selection when Change is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <GLAccountPicker
        accounts={makeAccounts()}
        value={3}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Change/i }));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
