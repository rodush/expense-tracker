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
  it('guides first-time users through the statement upload', () => {
    render(App);

    expect(screen.getByRole('heading', { level: 1, name: 'Make sense of your spending.' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Upload an expense statement' })).toBeTruthy();
    expect(screen.getByText('CSV, XLS, or XLSX · up to 5 MB')).toBeTruthy();
    expect(screen.queryByRole('region', { name: 'Spending overview' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Recent expenses' })).toBeNull();
  });

  it('filters locally, renders descriptions as text, and summarizes the filtered rows', async () => {
    uploadFile.mockResolvedValue({
      dataset_id: 'dataset-1',
      download_id: 'download-1',
      preview: [{
        date: '2026-01-01',
        amount: 12,
        who: 'Ava',
        category: 'Food',
        description: '<img src=x onerror=alert(1)>',
      }, {
        date: '2026-01-02', amount: 20, who: 'Mia', category: 'Travel', description: 'Train',
      }],
    });
    const { container } = render(App);

    await fireEvent.change(container.querySelector('#fileInput'), {
      target: { files: [new File(['data'], 'expenses.csv', { type: 'text/csv' })] },
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Analyze expenses' }));

    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Spending overview' })).toBeTruthy();
    expect(screen.getByRole('checkbox', { name: 'Food' })).toBeTruthy();
    expect(screen.getByRole('checkbox', { name: 'Ava' })).toBeTruthy();
    expect(container.querySelector('#resultsTable img')).toBeNull();
    await waitFor(() => expect(createOrUpdateCategoryChart).toHaveBeenCalledWith(
      expect.any(HTMLCanvasElement),
      expect.arrayContaining([
        expect.objectContaining({ name: 'Food', amount: 12, count: 1 }),
        expect.objectContaining({ name: 'Travel', amount: 20, count: 1 }),
      ]),
      expect.arrayContaining([12, 20]),
    ));
    expect(screen.getByText('32.00')).toBeTruthy();
    expect(fetchSummary).not.toHaveBeenCalled();

    await fireEvent.click(screen.getByRole('checkbox', { name: 'Food' }));
    expect(container.querySelector('#totalAmount').textContent).toBe('12.00');
    expect(screen.queryByText('Train')).toBeNull();
    expect(fetchSummary).not.toHaveBeenCalled();
    expect(screen.getByText('Spending totals by category', { selector: 'summary' })).toBeTruthy();
    expect(screen.getAllByRole('button', { name: /Sort by/ }).length).toBeGreaterThan(5);
  });
});
