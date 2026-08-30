import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  CheckCircleIcon,
  DocumentCheckIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { usersApi } from '@/services/users';
import type {
  UserImportConflictAction,
  UserImportPreview,
  UserImportResult,
} from '@/types/user';

const MAX_PACKAGE_BYTES = 128 * 1024 * 1024;
const CSV_TEMPLATE =
  'external_id,name,email,department,image_1,image_2,image_3,image_4,image_5\n' +
  'EMP-001,Ada Lovelace,ada@example.com,Engineering,images/EMP-001.jpg,,,,\n';

interface UserImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result: UserImportResult) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function downloadCsvTemplate(): void {
  const blob = new Blob([`\ufeff${CSV_TEMPLATE}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'people.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function UserImportModal({ isOpen, onClose, onSuccess }: UserImportModalProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const previewGenerationRef = useRef(0);
  const [packageFile, setPackageFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<UserImportPreview | null>(null);
  const [resolutions, setResolutions] = useState<
    Partial<Record<number, UserImportConflictAction>>
  >({});
  const [result, setResult] = useState<UserImportResult | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const previewMutation = useMutation({
    mutationFn: async ({ file, generation }: { file: File; generation: number }) => ({
      generation,
      preview: await usersApi.previewImport(file),
    }),
    onSuccess: ({ generation, preview: nextPreview }) => {
      if (generation !== previewGenerationRef.current) {
        return;
      }
      setPreview(nextPreview);
      setResolutions({});
      setLocalError(null);
    },
  });
  const importMutation = useMutation({
    mutationFn: async () => {
      if (packageFile === null || preview === null) {
        throw new Error('Review a ZIP package before importing.');
      }
      return usersApi.importPackage(
        packageFile,
        preview.package_sha256,
        preview.conflicts.map((conflict) => ({
          row: conflict.row,
          action: resolutions[conflict.row] as UserImportConflictAction,
        }))
      );
    },
    onSuccess: (importResult) => {
      setResult(importResult);
      onSuccess(importResult);
    },
  });

  const reset = () => {
    previewGenerationRef.current += 1;
    setPackageFile(null);
    setPreview(null);
    setResolutions({});
    setResult(null);
    setLocalError(null);
    previewMutation.reset();
    importMutation.reset();
    if (inputRef.current !== null) {
      inputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (importMutation.isPending) {
      return;
    }
    reset();
    onClose();
  };

  const handleFile = (file: File | undefined) => {
    previewGenerationRef.current += 1;
    setPreview(null);
    setResolutions({});
    setResult(null);
    previewMutation.reset();
    importMutation.reset();
    if (file === undefined) {
      setPackageFile(null);
      return;
    }
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setPackageFile(null);
      setLocalError('Choose a ZIP package containing people.csv and the referenced images.');
      return;
    }
    if (file.size > MAX_PACKAGE_BYTES) {
      setPackageFile(null);
      setLocalError('The ZIP package exceeds the 128 MB limit.');
      return;
    }
    setPackageFile(file);
    setLocalError(null);
  };

  const allConflictsResolved =
    preview !== null &&
    preview.conflicts.every((conflict) => {
      const action = resolutions[conflict.row];
      return action !== undefined && conflict.allowed_actions.includes(action);
    });
  const importableCount =
    preview === null
      ? 0
      : preview.ready_count +
        preview.conflicts.filter((conflict) => resolutions[conflict.row] === 'replace').length;
  const requestError =
    localError ?? previewMutation.error?.message ?? importMutation.error?.message ?? null;

  const renderPrimaryAction = () =>
    preview === null ? (
      <Button
        type="button"
        onClick={() => {
          if (packageFile !== null) {
            const generation = previewGenerationRef.current + 1;
            previewGenerationRef.current = generation;
            previewMutation.mutate({ file: packageFile, generation });
          }
        }}
        disabled={packageFile === null}
        isLoading={previewMutation.isPending}
        loadingText="Reviewing package"
      >
        Review package
      </Button>
    ) : (
      <Button
        type="button"
        onClick={() => importMutation.mutate()}
        disabled={preview.error_count > 0 || !allConflictsResolved || importableCount === 0}
        isLoading={importMutation.isPending}
        loadingText="Importing people"
      >
        Import {importableCount} {importableCount === 1 ? 'person' : 'people'}
      </Button>
    );

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Import people"
      description="Review one ZIP package, resolve every existing-person match, then import atomically."
      size="full"
      showCloseButton={!importMutation.isPending}
    >
      {result !== null ? (
        <div className="py-4 text-center" role="status" aria-live="polite">
          <CheckCircleIcon className="mx-auto h-12 w-12 text-green-600" aria-hidden="true" />
          <h3 className="mt-4 text-lg font-semibold text-gray-900">Import complete</h3>
          <p className="mx-auto mt-2 max-w-xl text-sm text-gray-600">
            Created {result.created_count}, replaced {result.replaced_count}, and skipped{' '}
            {result.skipped_count} people. Stored {result.embeddings_count} face embeddings.
          </p>
          <ModalFooter>
            <Button type="button" onClick={handleClose}>
              Close
            </Button>
          </ModalFooter>
        </div>
      ) : (
        <>
          <section aria-labelledby="package-format-heading">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 id="package-format-heading" className="font-semibold text-gray-900">
                  Package format
                </h3>
                <p className="mt-1 max-w-2xl text-sm text-gray-600">
                  Put <strong>people.csv</strong> at the ZIP root. Each row needs an external ID,
                  name, and image_1 path. Email, department, and image_2 through image_5 are
                  optional. Every imported account is a member.
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                leftIcon={<ArrowDownTrayIcon className="h-5 w-5" aria-hidden="true" />}
                onClick={downloadCsvTemplate}
                className="shrink-0"
              >
                Download CSV template
              </Button>
            </div>
            <ul className="mt-3 grid gap-1 text-sm text-gray-600 sm:grid-cols-2">
              <li>Up to 100 people per package</li>
              <li>JPEG or PNG; 1–5 images per person</li>
              <li>10 MB maximum per image</li>
              <li>128 MB maximum ZIP size</li>
            </ul>
          </section>

          <section className="mt-5 border-t border-gray-200 pt-5" aria-labelledby="upload-heading">
            <h3 id="upload-heading" className="font-semibold text-gray-900">
              Select package
            </h3>
            <label
              htmlFor="people-import-package"
              className="mt-3 flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-6 text-center transition-colors hover:border-primary-400 hover:bg-primary-50 focus-within:ring-2 focus-within:ring-primary-500 focus-within:ring-offset-2"
            >
              <ArrowUpTrayIcon className="h-8 w-8 text-gray-500" aria-hidden="true" />
              <span className="mt-2 text-sm font-medium text-gray-900">
                {packageFile === null ? 'Choose a ZIP package' : packageFile.name}
              </span>
              <span className="mt-1 text-xs text-gray-500">
                {packageFile === null
                  ? 'The package is checked before any database changes.'
                  : formatBytes(packageFile.size)}
              </span>
              <input
                ref={inputRef}
                id="people-import-package"
                type="file"
                accept=".zip,application/zip"
                className="sr-only"
                disabled={previewMutation.isPending || importMutation.isPending}
                onChange={(event) => handleFile(event.target.files?.[0])}
              />
            </label>
          </section>

          {requestError !== null && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
              {requestError}
            </div>
          )}

          {preview !== null && (
            <section className="mt-5 border-t border-gray-200 pt-5" aria-labelledby="review-heading">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 id="review-heading" className="font-semibold text-gray-900">
                    Review {preview.total_rows} CSV rows
                  </h3>
                  <p className="mt-1 text-sm text-gray-600">
                    {preview.ready_count} new, {preview.conflict_count} existing-person matches,{' '}
                    {preview.error_count} errors.
                  </p>
                </div>
                {preview.error_count === 0 && preview.conflict_count === 0 && (
                  <span className="inline-flex items-center gap-2 text-sm font-medium text-green-700">
                    <DocumentCheckIcon className="h-5 w-5" aria-hidden="true" />
                    Ready to import
                  </span>
                )}
              </div>

              {preview.errors.length > 0 && (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-900" role="alert">
                  <div className="flex items-center gap-2 font-medium">
                    <ExclamationTriangleIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
                    Fix these package errors and review the ZIP again
                  </div>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                    {preview.errors.map((error, index) => (
                      <li key={`${error.row ?? 'package'}-${error.code}-${index}`}>
                        {error.row === null ? '' : `Row ${error.row}: `}
                        {error.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {preview.conflicts.length > 0 && (
                <div className="mt-4" aria-labelledby="conflicts-heading">
                  <h4 id="conflicts-heading" className="text-sm font-semibold text-gray-900">
                    Resolve existing-person matches
                  </h4>
                  <p className="mt-1 text-sm text-gray-600">
                    Choose what to do for each match. Replace updates member profile fields and face
                    enrollment; skip leaves the existing person unchanged.
                  </p>
                  <div className="mt-3 max-h-80 divide-y divide-gray-200 overflow-y-auto rounded-lg border border-gray-200" tabIndex={0} aria-label="Import conflicts">
                    {preview.conflicts.map((conflict) => (
                      <fieldset key={conflict.row} className="p-4">
                        <legend className="text-sm font-semibold text-gray-900">
                          Row {conflict.row}: {conflict.name}
                        </legend>
                        <p className="mt-1 text-sm text-gray-600">
                          External ID {conflict.external_id} matches {conflict.existing_name}.
                        </p>
                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          <label
                            className={`flex min-h-11 items-center gap-3 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-800 has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50 ${
                              importMutation.isPending
                                ? 'cursor-not-allowed opacity-60'
                                : 'cursor-pointer'
                            }`}
                          >
                            <input
                              type="radio"
                              name={`resolution-${conflict.row}`}
                              value="skip"
                              checked={resolutions[conflict.row] === 'skip'}
                              disabled={importMutation.isPending}
                              onChange={() =>
                                setResolutions((current) => ({
                                  ...current,
                                  [conflict.row]: 'skip',
                                }))
                              }
                            />
                            Skip this row
                          </label>
                          {conflict.allowed_actions.includes('replace') ? (
                            <label
                              className={`flex min-h-11 items-center gap-3 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-800 has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50 ${
                                importMutation.isPending
                                  ? 'cursor-not-allowed opacity-60'
                                  : 'cursor-pointer'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`resolution-${conflict.row}`}
                                value="replace"
                                checked={resolutions[conflict.row] === 'replace'}
                                disabled={importMutation.isPending}
                                onChange={() =>
                                  setResolutions((current) => ({
                                    ...current,
                                    [conflict.row]: 'replace',
                                  }))
                                }
                              />
                              Replace profile and faces
                            </label>
                          ) : (
                            <p className="flex min-h-11 items-center rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">
                              Elevated accounts cannot be replaced in bulk.
                            </p>
                          )}
                        </div>
                      </fieldset>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {importMutation.isPending && (
            <div className="mt-4 rounded-lg bg-primary-50 px-4 py-3 text-sm text-primary-900" role="status" aria-live="polite">
              Analyzing every face and applying the import. Keep this dialog open; no database changes
              are saved unless the whole package succeeds.
            </div>
          )}

          <div className="-mx-4 -mb-4 mt-4 border-t border-gray-100 px-4 py-4 sm:-mx-6 sm:px-6">
            <div className="flex flex-col gap-3 sm:hidden">
              {renderPrimaryAction()}
              <Button
                type="button"
                variant="secondary"
                onClick={handleClose}
                disabled={importMutation.isPending}
              >
                Cancel
              </Button>
            </div>
            <div className="hidden items-center justify-end gap-3 sm:flex">
              <Button
                type="button"
                variant="secondary"
                onClick={handleClose}
                disabled={importMutation.isPending}
              >
                Cancel
              </Button>
              {renderPrimaryAction()}
            </div>
          </div>
        </>
      )}
    </Modal>
  );
}

export default UserImportModal;
