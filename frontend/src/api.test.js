import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildExportUrl, fetchSummary, uploadFile } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('frontend API client', () => {
  it('posts the selected expense file as multipart form data', async () => {
    const file = new File(['date,amount'], 'expenses.csv', { type: 'text/csv' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ dataset_id: 'dataset-1' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await uploadFile(file);

    expect(fetchMock).toHaveBeenCalledWith('/upload', {
      method: 'POST',
      body: expect.any(FormData),
    });
    expect(fetchMock.mock.calls[0][1].body.get('file')).toBe(file);
  });

  it('sends repeated category and person filters to the summary API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ expense_count: 1 }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await fetchSummary('dataset/1', ['Food', 'Transport'], ['Ava'], undefined);

    const [url] = fetchMock.mock.calls[0];
    const query = new URL(url, 'http://localhost').searchParams;
    expect(query.getAll('category')).toEqual(['Food', 'Transport']);
    expect(query.getAll('who')).toEqual(['Ava']);
    expect(url).toContain('/datasets/dataset%2F1/summary?');
  });

  it('builds the filtered export URL using repeated filters', () => {
    const url = buildExportUrl('dataset/1', ['Food', 'Transport'], ['Ava']);
    const query = new URL(url, 'http://localhost').searchParams;

    expect(url).toContain('/datasets/dataset%2F1/export?');
    expect(query.getAll('category')).toEqual(['Food', 'Transport']);
    expect(query.getAll('who')).toEqual(['Ava']);
  });
});
