import { queryClient } from '@/lib/queryClient';

const LEGACY_PRIVATE_CACHES = ['api-cache', 'api-v1-cache'] as const;

export async function clearLegacyApiCaches(): Promise<void> {
  if (!('caches' in globalThis)) {
    return;
  }
  await Promise.all(LEGACY_PRIVATE_CACHES.map((cacheName) => globalThis.caches.delete(cacheName)));
}

export function clearPrivateClientState(): void {
  queryClient.clear();
  void clearLegacyApiCaches();
}
