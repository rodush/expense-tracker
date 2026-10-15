import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App.svelte';
import { fetchSummary, uploadFile } from './api';
import { createOrUpdateCategoryChart } from './chart';

vi.mock('./api', () => ({
  uploadFile: vi.fn(),
  fetchSummary: vi.fn(),
  buildExportUrl: vi.fn(() => '/export'),
}));

vi.mock('./chart', () => ({
  createOrUpdateCategoryChart: vi.fn(),
  destroyCategoryChart: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('expense dashboard', () => {
  it('renders uploaded descriptions as text and sends categories to the chart', async () => {
    uploadFile.mockResolvedValue({
      dataset_id: 'dataset-1',
      download_id: 'download-1',
      preview: [{
        date: '2026-01-01',
        amount: 12,
        who: 'Ava',
        category: 'Food',
        description: '<img src=x onerror=alert(1)>',
      }],
    });
    fetchSummary.mockResolvedValue({
      expense_count: 1,
      total_amount: 12,
      categories: [{ name: 'Food', amount: 12, count: 1 }],
      who: [{ name: 'Ava', amount: 12, count: 1 }],
    });
    const { container } = render(App);

    await fireEvent.change(container.querySelector('#fileInput'), {
      target: { files: [new File(['data'], 'expenses.csv', { type: 'text/csv' })] },
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Upload & Categorize' }));

    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeTruthy();
    expect(container.querySelector('#resultsTable img')).toBeNull();
    await waitFor(() => expect(createOrUpdateCategoryChart).toHaveBeenCalledWith(
      expect.any(HTMLCanvasElement),
      [{ name: 'Food', amount: 12, count: 1 }],
      [12],
    ));
  });
});
