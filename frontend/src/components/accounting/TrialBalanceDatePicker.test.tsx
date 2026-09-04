// Milestone 17 · Increment 2 (SESSION_145) — TrialBalanceDatePicker tests.
// SESSION_244 (walk finding 53): the browser-zone helpers ``todayIsoDate``
// and ``dateToEndOfDayIso`` were removed from this file. Their store-zone
// replacements live in ``lib/storeTime.ts`` and are covered by
// ``storeTime.test.ts``.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TrialBalanceDatePicker } from "@/components/accounting/TrialBalanceDatePicker";


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
