// Milestone 17 · Increment 2 (SESSION_145) — TrialBalanceDatePicker tests.
//
// Covers the pure helpers (``todayIsoDate`` + ``dateToEndOfDayIso``) and
// the controlled-component surface. The picker's ``onChange`` is what
// the parent page wires to a refetch — asserting it fires on native
// change is the load-bearing contract.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  TrialBalanceDatePicker,
  dateToEndOfDayIso,
  todayIsoDate,
} from "@/components/accounting/TrialBalanceDatePicker";


describe("todayIsoDate", () => {
  it("returns a YYYY-MM-DD string matching the browser today", () => {
    const iso = todayIsoDate();
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    const now = new Date();
    const expected = `${now.getFullYear()}-${String(
      now.getMonth() + 1,
    ).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    expect(iso).toBe(expected);
  });
});


describe("dateToEndOfDayIso", () => {
  it("converts YYYY-MM-DD to an ISO timestamp at 23:59:59 local", () => {
    const iso = dateToEndOfDayIso("2026-05-31");
    // Reparse and confirm date components come back as May 31 local.
    const parsed = new Date(iso);
    expect(parsed.getFullYear()).toBe(2026);
    expect(parsed.getMonth()).toBe(4); // May = index 4
    expect(parsed.getDate()).toBe(31);
    expect(parsed.getHours()).toBe(23);
    expect(parsed.getMinutes()).toBe(59);
    expect(parsed.getSeconds()).toBe(59);
  });
});


describe("TrialBalanceDatePicker component", () => {
  it("renders a date input with the supplied value", () => {
    render(
      <TrialBalanceDatePicker value="2026-08-02" onChange={() => {}} />,
    );
    const input = screen.getByLabelText(/As of/i) as HTMLInputElement;
    expect(input.type).toBe("date");
    expect(input.value).toBe("2026-08-02");
  });

  it("fires onChange with the new value when the user picks a date", () => {
    const onChange = vi.fn();
    render(
      <TrialBalanceDatePicker value="2026-08-02" onChange={onChange} />,
    );
    const input = screen.getByLabelText(/As of/i);
    fireEvent.change(input, { target: { value: "2026-05-31" } });
    expect(onChange).toHaveBeenCalledWith("2026-05-31");
  });

  it("disables the input when disabled=true", () => {
    render(
      <TrialBalanceDatePicker
        value="2026-08-02"
        onChange={() => {}}
        disabled
      />,
    );
    const input = screen.getByLabelText(/As of/i) as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });

  it("uses the custom label when supplied", () => {
    render(
      <TrialBalanceDatePicker
        value="2026-08-02"
        onChange={() => {}}
        label="Period end"
      />,
    );
    expect(screen.getByLabelText(/Period end/i)).toBeInTheDocument();
  });
});
