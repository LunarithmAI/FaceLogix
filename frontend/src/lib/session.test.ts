import { afterEach, describe, expect, it, vi } from 'vitest';
import { queryClient } from '@/lib/queryClient';
import { clearPrivateClientState } from '@/lib/session';

describe('private client cleanup', () => {
  afterEach(() => {
    queryClient.clear();
    vi.unstubAllGlobals();
  });

  it('purges private queries and both legacy API caches', async () => {
    const deleteCache = vi.fn().mockResolvedValue(true);
    vi.stubGlobal('caches', { delete: deleteCache });
    queryClient.setQueryData(['users'], { items: [{ id: 'private-user' }] });

    clearPrivateClientState();
    await vi.waitFor(() => expect(deleteCache).toHaveBeenCalledTimes(2));
    expect(queryClient.getQueryData(['users'])).toBeUndefined();
    expect(deleteCache).toHaveBeenCalledWith('api-cache');
    expect(deleteCache).toHaveBeenCalledWith('api-v1-cache');
  });
});
