import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UserImportModal } from '@/components/admin/UserImportModal';
import type { UserImportPreview, UserImportResult } from '@/types/user';

const userImportMocks = vi.hoisted(() => ({
  previewImport: vi.fn(),
  importPackage: vi.fn(),
}));

vi.mock('@/services/users', () => ({
  usersApi: userImportMocks,
}));

function ImportHarness() {
  const [isOpen, setIsOpen] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)}>
        Open import
      </button>
      <UserImportModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onSuccess={vi.fn()}
      />
    </>
  );
}

describe('people import workflow', () => {
  beforeEach(() => {
    userImportMocks.previewImport.mockReset();
    userImportMocks.importPackage.mockReset();
  });

  it('requires a manual resolution for each conflict before importing', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    const packageFile = new File(['zip'], 'people.zip', { type: 'application/zip' });
    userImportMocks.previewImport.mockResolvedValue({
      package_sha256: 'a'.repeat(64),
      total_rows: 2,
      ready_count: 1,
      conflict_count: 1,
      error_count: 0,
      errors: [],
      conflicts: [
        {
          row: 2,
          external_id: 'EMP-1',
          email: 'ada@example.com',
          name: 'Ada Lovelace',
          existing_user_id: 'existing-user',
          existing_name: 'Ada L.',
          allowed_actions: ['skip', 'replace'],
        },
      ],
    });
    let resolveImport!: (result: UserImportResult) => void;
    userImportMocks.importPackage.mockReturnValue(
      new Promise<UserImportResult>((resolve) => {
        resolveImport = resolve;
      })
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <UserImportModal isOpen onClose={vi.fn()} onSuccess={onSuccess} />
      </QueryClientProvider>
    );
    await user.upload(screen.getByLabelText(/choose a zip package/i), packageFile);
    await user.click(screen.getAllByRole('button', { name: 'Review package' })[0]);

    expect(await screen.findByText('Review 2 CSV rows')).toBeInTheDocument();
    const importButton = screen.getAllByRole('button', { name: 'Import 1 person' })[0];
    expect(importButton).toBeDisabled();

    await user.click(screen.getByRole('radio', { name: 'Replace profile and faces' }));
    expect(screen.getAllByRole('button', { name: 'Import 2 people' })[0]).toBeEnabled();
    await user.click(screen.getAllByRole('button', { name: 'Import 2 people' })[0]);
    expect(screen.getByRole('radio', { name: 'Replace profile and faces' })).toBeDisabled();
    expect(screen.getByRole('radio', { name: 'Skip this row' })).toBeDisabled();

    await waitFor(() =>
      expect(userImportMocks.importPackage).toHaveBeenCalledWith(packageFile, 'a'.repeat(64), [
        { row: 2, action: 'replace' },
      ])
    );
    act(() => {
      resolveImport({
        total_rows: 2,
        created_count: 1,
        replaced_count: 1,
        skipped_count: 0,
        embeddings_count: 2,
      });
    });
    expect(await screen.findByText('Import complete')).toBeInTheDocument();
    expect(screen.getByText(/Created 1, replaced 1, and skipped 0 people/)).toBeInTheDocument();
    expect(onSuccess).toHaveBeenCalledWith({
      total_rows: 2,
      created_count: 1,
      replaced_count: 1,
      skipped_count: 0,
      embeddings_count: 2,
    });
  });

  it('ignores a preview response after the dialog is reset', async () => {
    const user = userEvent.setup();
    let resolvePreview!: (preview: UserImportPreview) => void;
    userImportMocks.previewImport.mockReturnValue(
      new Promise<UserImportPreview>((resolve) => {
        resolvePreview = resolve;
      })
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <ImportHarness />
      </QueryClientProvider>
    );

    await user.upload(
      screen.getByLabelText(/choose a zip package/i),
      new File(['zip'], 'people.zip', { type: 'application/zip' })
    );
    await user.click(screen.getAllByRole('button', { name: 'Review package' })[0]);
    await user.click(screen.getAllByRole('button', { name: 'Cancel' })[0]);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    act(() => {
      resolvePreview({
        package_sha256: 'a'.repeat(64),
        total_rows: 1,
        ready_count: 1,
        conflict_count: 0,
        error_count: 0,
        errors: [],
        conflicts: [],
      });
    });
    await user.click(screen.getByRole('button', { name: 'Open import' }));

    expect(screen.queryByText('Review 1 CSV rows')).not.toBeInTheDocument();
    expect(screen.getByText('Choose a ZIP package')).toBeInTheDocument();
  });
});
