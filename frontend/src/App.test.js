import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App.svelte";
import {
  buildExportUrl,
  fetchExpenses,
  fetchFilterOptions,
  fetchSummary,
  uploadFile,
} from "./api";
import { formatTransactionDate } from "./date-format";

vi.mock("./api", () => ({
  uploadFile: vi.fn(),
  fetchExpenses: vi.fn(),
  fetchFilterOptions: vi.fn(),
  fetchSummary: vi.fn(),
  buildExportUrl: vi.fn(() => "/expenses/export"),
}));

vi.mock("./chart", () => ({
  createOrUpdateCategoryChart: vi.fn(),
  destroyCategoryChart: vi.fn(),
}));

const rows = [
  {
    date: "2026-01-01",
    amount: 12,
    who: "Ava",
    category: "Food",
    description: "<img src=x onerror=alert(1)>",
  },
];

function mockHistory({ items = rows, total_count = items.length } = {}) {
  fetchFilterOptions.mockResolvedValue({
    categories: ["Food", "Travel"],
    who: ["Ava", "Mia"],
    years: [2026, 2025],
  });
  fetchExpenses.mockResolvedValue({ items, total_count, limit: 25, offset: 0 });
  fetchSummary.mockResolvedValue({
    expense_count: items.length,
    total_amount: 12,
    categories: [{ name: "Food", amount: 12, count: 1, percentage: 100 }],
    who: [{ name: "Ava", amount: 12, count: 1 }],
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("historical expense dashboard", () => {
  it("shows the upload action and loads saved expenses on first visit", async () => {
    mockHistory();
    render(App);

    expect(
      screen.getByRole("heading", { name: "Make sense of your spending." }),
    ).toBeTruthy();
    expect(
      screen.getByRole("region", { name: "Upload an expense statement" }),
    ).toBeTruthy();
    expect(
      await screen.findByText("<img src=x onerror=alert(1)>"),
    ).toBeTruthy();
    expect(screen.getByText(formatTransactionDate(rows[0].date))).toBeTruthy();
    expect(screen.queryByText(rows[0].date)).toBeNull();
    expect(fetchFilterOptions).toHaveBeenCalledOnce();
    expect(fetchExpenses).toHaveBeenCalledWith(
      expect.objectContaining({ offset: 0, limit: 25 }),
    );
    expect(fetchSummary).toHaveBeenCalled();
  });

  it("loads filtered history for category, person, date range and quick month/year selectors", async () => {
    mockHistory();
    render(App);
    await screen.findByText("<img src=x onerror=alert(1)>");

    await fireEvent.click(screen.getByRole("checkbox", { name: "Food" }));
    await waitFor(() =>
      expect(fetchExpenses).toHaveBeenLastCalledWith(
        expect.objectContaining({ categories: ["Food"] }),
      ),
    );
    await fireEvent.input(screen.getByLabelText("From date"), {
      target: { value: "2026-01-01" },
    });
    await waitFor(() =>
      expect(fetchExpenses).toHaveBeenLastCalledWith(
        expect.objectContaining({
          dateFrom: "2026-01-01",
          year: "",
          month: "",
        }),
      ),
    );
    await fireEvent.change(screen.getByLabelText("Year"), {
      target: { value: "2026" },
    });
    await waitFor(() =>
      expect(fetchExpenses).toHaveBeenLastCalledWith(
        expect.objectContaining({ dateFrom: "", year: "2026" }),
      ),
    );
    await fireEvent.change(screen.getByLabelText("Month"), {
      target: { value: "1" },
    });
    await waitFor(() =>
      expect(fetchExpenses).toHaveBeenLastCalledWith(
        expect.objectContaining({ year: "2026", month: "1" }),
      ),
    );
  });

  it("paginates the saved history and exports with the active filters", async () => {
    mockHistory({ total_count: 40 });
    render(App);
    await screen.findByText("<img src=x onerror=alert(1)>");

    await fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() =>
      expect(fetchExpenses).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: 25, limit: 25 }),
      ),
    );
    expect(buildExportUrl).toHaveBeenLastCalledWith(
      expect.objectContaining({ categories: [], who: [] }),
    );
    expect(
      screen.getByRole("link", { name: /Download filtered CSV/ }),
    ).toBeTruthy();
  });

  it("keeps transaction sorting available", async () => {
    const olderRow = {
      ...rows[0],
      date: "2025-01-01",
      amount: 3,
      description: "Older expense",
    };
    mockHistory({ items: [rows[0], olderRow], total_count: 2 });
    render(App);
    await screen.findByText("<img src=x onerror=alert(1)>");

    const amountSortButtons = screen.getAllByRole("button", {
      name: "Sort by Amount",
    });
    await fireEvent.click(amountSortButtons[amountSortButtons.length - 1]);

    const tableRows = screen
      .getByRole("table", { name: "Expenses included in the current report" })
      .querySelectorAll("tbody tr");
    expect(tableRows[0].textContent).toContain("Older expense");
    expect(tableRows[1].textContent).toContain("<img src=x onerror=alert(1)>");
  });

  it("refreshes the shared history after an upload and reports duplicate counts", async () => {
    mockHistory({ items: [], total_count: 0 });
    uploadFile.mockResolvedValue({
      row_count: 5,
      new_transaction_count: 3,
      duplicate_count: 2,
    });
    const { container } = render(App);

    await fireEvent.change(container.querySelector("#fileInput"), {
      target: {
        files: [new File(["data"], "expenses.csv", { type: "text/csv" })],
      },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: "Analyze expenses" }),
    );

    expect(
      await screen.findByText(/3 new expenses added; 2 duplicates skipped/),
    ).toBeTruthy();
    await waitFor(() =>
      expect(fetchExpenses.mock.calls.length).toBeGreaterThan(1),
    );
    expect(
      screen.queryByRole("heading", { name: "Make sense of your spending." }),
    ).toBeNull();
    expect(
      screen.getAllByRole("region", { name: "Expense history" }),
    ).toHaveLength(2);
    expect(screen.getByRole("checkbox", { name: "Food" })).toBeTruthy();
  });
});
