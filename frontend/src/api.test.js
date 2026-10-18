import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildExportUrl, fetchExpenses, fetchFilterOptions, fetchSummary, uploadFile } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('frontend API client', () => {
  it('posts the selected expense file as multipart form data', async () => {
    const file = new File(['date,amount'], 'expenses.csv', { type: 'text/csv' });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ row_count: 1 }) });
    vi.stubGlobal('fetch', fetchMock);

    await uploadFile(file);

    expect(fetchMock).toHaveBeenCalledWith('/upload', { method: 'POST', body: expect.any(FormData) });
    expect(fetchMock.mock.calls[0][1].body.get('file')).toBe(file);
  });

  it('sends repeated and scalar filters to the historical expense endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [], total_count: 0 }) });
    vi.stubGlobal('fetch', fetchMock);
    const filters = {
      categories: ['Food', 'Travel'], who: ['Ava'], dateFrom: '2026-01-01', dateTo: '2026-01-31',
      year: 2026, month: 1, limit: 25, offset: 50,
    };

    await fetchExpenses(filters);

    const [url] = fetchMock.mock.calls[0];
    const query = new URL(url, 'http://localhost').searchParams;
    expect(url).toContain('/expenses?');
    expect(query.getAll('category')).toEqual(['Food', 'Travel']);
    expect(query.getAll('who')).toEqual(['Ava']);
    expect(query.get('date_from')).toBe('2026-01-01');
    expect(query.get('date_to')).toBe('2026-01-31');
    expect(query.get('year')).toBe('2026');
    expect(query.get('month')).toBe('1');
    expect(query.get('limit')).toBe('25');
    expect(query.get('offset')).toBe('50');
  });

  it('requests history filter options and summary without a dataset id', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ categories: [], who: [], years: [] }) });
    vi.stubGlobal('fetch', fetchMock);
    const filters = { categories: ['Food'], who: ['Ava'], dateFrom: '', dateTo: '', year: '', month: '' };

    await fetchFilterOptions();
    await fetchSummary(filters);

    expect(fetchMock.mock.calls[0][0]).toBe('/expenses/filter-options');
    expect(fetchMock.mock.calls[1][0]).toContain('/expenses/summary?');
    expect(new URL(fetchMock.mock.calls[1][0], 'http://localhost').searchParams.getAll('category')).toEqual(['Food']);
  });

  it('builds a filtered history export URL', () => {
    const url = buildExportUrl({ categories: ['Food'], who: ['Ava'], dateFrom: '2026-01-01', dateTo: '', year: '', month: '' });
    const query = new URL(url, 'http://localhost').searchParams;
    expect(url).toContain('/expenses/export?');
    expect(query.getAll('category')).toEqual(['Food']);
    expect(query.getAll('who')).toEqual(['Ava']);
    expect(query.get('date_from')).toBe('2026-01-01');
  });
});
