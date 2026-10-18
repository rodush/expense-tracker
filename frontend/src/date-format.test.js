import { describe, expect, it } from "vitest";
import { formatTransactionDate } from "./date-format";

describe("formatTransactionDate", () => {
  it("formats calendar dates using the requested locale", () => {
    expect(formatTransactionDate("2026-01-02", "en-GB")).toBe("2 Jan 2026");
    expect(formatTransactionDate("2026-01-02", "en-US")).toBe("Jan 2, 2026");
  });

  it("preserves blank and invalid date values", () => {
    expect(formatTransactionDate("")).toBe("");
    expect(formatTransactionDate("not-a-date")).toBe("not-a-date");
    expect(formatTransactionDate("2026-02-30", "en-GB")).toBe("2026-02-30");
  });
});
