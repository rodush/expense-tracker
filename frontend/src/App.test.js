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
      screen.getByText("Upload an expense statement").closest("summary"),
    ).toBeTruthy();
    expect(
      screen.getByText("Upload an expense statement").closest("details").open,
    ).toBe(false);
    await fireEvent.click(screen.getByText("Upload an expense statement"));
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
    await fireEvent.change(screen.getByLabelText("From date"), {
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
    expect(fetchExpenses).toHaveBeenLastCalledWith(
      expect.objectContaining({
        sortBy: "amount",
        sortDirection: "asc",
        offset: 0,
      }),
    );
    expect(tableRows[0].textContent).toContain("<img src=x onerror=alert(1)>");
    expect(tableRows[1].textContent).toContain("Older expense");
  });

  it("shows the selected filter count when the filters are collapsed", async () => {
    mockHistory();
    render(App);
    await screen.findByText("<img src=x onerror=alert(1)>");

    await fireEvent.click(screen.getByRole("checkbox", { name: "Food" }));
    await fireEvent.click(screen.getByRole("checkbox", { name: "Ava" }));
    const filterSummary = screen
      .getByText("Filter your expenses")
      .closest("summary");
    await fireEvent.click(filterSummary);

    expect(filterSummary.closest("details").open).toBe(false);
    expect(screen.getByText("2 selected filters")).toBeTruthy();
  });

  it("leads the report with total spend", async () => {
    mockHistory();
    render(App);
    await screen.findByText("<img src=x onerror=alert(1)>");

    const totalSpend = screen.getByText("Total spend").closest(".summary-card");
    expect(totalSpend.parentElement.classList.contains("dashboard")).toBe(true);
    expect(
      screen.queryByText("Transactions", { selector: ".metric-label" }),
    ).toBeNull();
    expect(document.querySelector("#expenseCount")).toBeNull();
  });

  it("refreshes the shared history after an upload and reports duplicate counts", async () => {
    mockHistory({ items: [], total_count: 0 });
    uploadFile.mockResolvedValue({
      row_count: 5,
      new_transaction_count: 3,
      duplicate_count: 2,
    });
    const { container } = render(App);

    await fireEvent.click(screen.getByText("Upload an expense statement"));
    await fireEvent.change(container.querySelector("#fileInput"), {
      target: {
        files: [new File(["data"], "expenses.csv", { type: "text/csv" })],
      },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: "Import expenses" }),
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
    ).toHaveLength(1);
    expect(screen.getByRole("checkbox", { name: "Food" })).toBeTruthy();
    expect(container.querySelector(".upload-accordion").open).toBe(false);
  });
});

it("clears stale totals and export after a failed refresh and allows retry", async () => {
  mockHistory();
  render(App);
  await screen.findByText("<img src=x onerror=alert(1)>");
  fetchExpenses.mockRejectedValueOnce(new Error("Could not refresh"));
  await fireEvent.click(screen.getByRole("checkbox", { name: "Food" }));
  await screen.findByText("Could not refresh");
  expect(screen.queryByText("Total spend")).toBeNull();
  expect(
    screen.queryByRole("link", { name: /Download filtered CSV/ }),
  ).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "Retry report" }));
  await screen.findByText("<img src=x onerror=alert(1)>");
});

it("shows first-import guidance and opens upload for an empty ledger", async () => {
  mockHistory({ items: [], total_count: 0 });
  fetchFilterOptions.mockResolvedValue({ categories: [], who: [], years: [] });
  render(App);
  await screen.findByText(
    "Your ledger is empty. Import a statement to get started.",
  );
  expect(
    screen.getByText("Upload an expense statement").closest("details").open,
  ).toBe(true);
});

it("keeps filter errors independent from a successful report", async () => {
  mockHistory();
  fetchFilterOptions.mockRejectedValueOnce(new Error("Filters unavailable"));
  render(App);
  await screen.findByText("<img src=x onerror=alert(1)>");
  expect(screen.getByText("Filters unavailable")).toBeTruthy();
  await fireEvent.click(screen.getByRole("button", { name: "Retry filters" }));
  await waitFor(() =>
    expect(screen.queryByText("Filters unavailable")).toBeNull(),
  );
});

it("rejects reversed dates without requesting a misleading report", async () => {
  mockHistory();
  render(App);
  await screen.findByText("<img src=x onerror=alert(1)>");
  await fireEvent.change(screen.getByLabelText("From date"), {
    target: { value: "2026-02-01" },
  });
  const calls = fetchExpenses.mock.calls.length;
  await fireEvent.change(screen.getByLabelText("To date"), {
    target: { value: "2026-01-01" },
  });
  await screen.findByText("The start date must not be after the end date.");
  expect(fetchExpenses.mock.calls.length).toBe(calls);
  expect(
    screen.queryByRole("link", { name: /Download filtered CSV/ }),
  ).toBeNull();
});

it("ignores responses from an older filter request", async () => {
  mockHistory();
  render(App);
  await screen.findByText("<img src=x onerror=alert(1)>");
  let finish;
  fetchExpenses.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await fireEvent.click(screen.getByRole("checkbox", { name: "Food" }));
  await fireEvent.click(screen.getByRole("checkbox", { name: "Travel" }));
  await screen.findByText("<img src=x onerror=alert(1)>");
  finish({
    items: [{ ...rows[0], description: "Stale response" }],
    total_count: 1,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByText("Stale response")).toBeNull();
});
