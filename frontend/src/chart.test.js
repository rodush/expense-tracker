import { beforeEach, describe, expect, it, vi } from "vitest";

const charts = [];
vi.mock("chart.js/auto", () => ({
  default: class MockChart {
    constructor(_canvas, config) {
      this.config = config;
      this.data = config.data;
      this.options = config.options;
      this.update = vi.fn();
      this.destroy = vi.fn();
      charts.push(this);
    }
  },
}));

const { createOrUpdateCategoryChart, destroyCategoryChart } =
  await import("./chart");

beforeEach(() => {
  destroyCategoryChart();
  charts.length = 0;
});

describe("category chart", () => {
  it("uses updated category amounts in tooltip callbacks after filtering", () => {
    const canvas = document.createElement("canvas");
    createOrUpdateCategoryChart(canvas, [{ name: "Food", amount: 20 }], [20]);
    const chart = charts[0];

    createOrUpdateCategoryChart(canvas, [{ name: "Food", amount: 8 }], [8]);

    expect(
      chart.config.options.plugins.tooltip.callbacks.label({
        label: "Food",
        dataIndex: 0,
      }),
    ).toBe("Food: 8.00");
  });

  it("places the category legend beside the doughnut chart", () => {
    createOrUpdateCategoryChart(
      document.createElement("canvas"),
      [{ name: "Food", amount: 20 }],
      [20],
    );

    expect(charts[0].config.options.plugins.legend.position).toBe("right");
  });
});
