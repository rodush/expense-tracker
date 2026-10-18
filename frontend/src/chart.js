import Chart from "chart.js/auto";

let categoryChart = null;

export function createOrUpdateCategoryChart(
  canvas,
  items,
  categoryChartAmounts,
) {
  const categories = [
    ...new Map(items.map((item) => [item.name, item])).values(),
  ];
  const labels = categories.map((item) => item.name);
  const values = categories.map((item) => Math.abs(item.amount));
  const colors = categories.map(
    (_, index) => `hsl(${(index * 360) / categories.length} 70% 48%)`,
  );

  if (!categoryChart && canvas) {
    categoryChart = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
            borderWidth: 2,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        cutout: "62%",
        maintainAspectRatio: false,
        responsive: true,
        plugins: {
          legend: { position: "right" },
          tooltip: {
            callbacks: {
              label: (context) =>
                `${context.label}: ${formatAmount(categoryChartAmounts[context.dataIndex])}`,
            },
          },
        },
      },
    });
    return categoryChart;
  }

  if (categoryChart) {
    categoryChart.data.labels = labels;
    categoryChart.data.datasets[0].data = values;
    categoryChart.data.datasets[0].backgroundColor = colors;
    categoryChart.options.plugins.tooltip.callbacks.label = (context) =>
      `${context.label}: ${formatAmount(categoryChartAmounts[context.dataIndex])}`;
    categoryChart.update();
  }
  return categoryChart;
}

export function destroyCategoryChart() {
  categoryChart?.destroy();
  categoryChart = null;
}

function formatAmount(amount) {
  return Number(amount).toFixed(2);
}
