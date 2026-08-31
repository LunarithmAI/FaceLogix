import { useEffect, useId, useRef } from 'react';
import type { MouseEvent, ReactNode } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { translate as t } from '@/i18n';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  showCloseButton?: boolean;
}

const sizeStyles = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-4xl',
};

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  showCloseButton = true,
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog === null) {
      return;
    }
    if (isOpen && !dialog.open) {
      previousFocusRef.current = document.activeElement as HTMLElement | null;
      dialog.showModal();
      const firstFocusTarget = dialog.querySelector<HTMLElement>(
        '[autofocus], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      firstFocusTarget?.focus();
    } else if (!isOpen && dialog.open) {
      dialog.close();
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
    }
  }, [isOpen]);

  useEffect(
    () => () => {
      previousFocusRef.current?.focus();
    },
    []
  );

  const handleOutsideClick = (event: MouseEvent<HTMLDialogElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={title === undefined ? undefined : titleId}
      aria-describedby={description === undefined ? undefined : descriptionId}
      className="m-auto max-h-none w-full max-w-none bg-transparent p-4 backdrop:bg-black/50 backdrop:backdrop-blur-sm"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          onClose();
        }
      }}
      onClick={handleOutsideClick}
    >
      <div
        className={`mx-auto flex max-h-[calc(100dvh-2rem)] w-full ${sizeStyles[size]} flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl`}
        onClick={(event) => event.stopPropagation()}
      >
        {(title !== undefined || showCloseButton) && (
          <div className="flex shrink-0 items-start justify-between gap-4 border-b border-gray-100 px-4 py-4 sm:px-6">
            <div>
              {title !== undefined && (
                <h2 id={titleId} className="text-lg font-semibold text-gray-900">
                  {title}
                </h2>
              )}
              {description !== undefined && (
                <p id={descriptionId} className="mt-1 text-sm text-gray-600">
                  {description}
                </p>
              )}
            </div>
            {showCloseButton && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="-mr-2 min-w-11 shrink-0 px-2"
                aria-label={t('Close dialog')}
              >
                <XMarkIcon className="h-5 w-5" aria-hidden="true" />
              </Button>
            )}
          </div>
        )}
        <div className="overflow-y-auto px-4 py-4 sm:px-6">{isOpen ? children : null}</div>
      </div>
    </dialog>
  );
}

interface ModalFooterProps {
  children: ReactNode;
  className?: string;
}

export function ModalFooter({ children, className = '' }: ModalFooterProps) {
  return (
    <div
      className={`-mx-4 -mb-4 mt-4 flex flex-col-reverse gap-3 border-t border-gray-100 px-4 py-4 sm:-mx-6 sm:flex-row sm:items-center sm:justify-end sm:px-6 ${className}`}
    >
      {children}
    </div>
  );
}

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'primary';
  isLoading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = t('Confirm'),
  cancelText = t('Cancel'),
  variant = 'primary',
  isLoading = false,
}: ConfirmModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} description={message} size="sm">
      <ModalFooter>
        <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
          {cancelText}
        </Button>
        <Button
          type="button"
          variant={variant}
          onClick={onConfirm}
          isLoading={isLoading}
          loadingText={variant === 'danger' ? t('Deleting') : t('Working')}
        >
          {confirmText}
        </Button>
      </ModalFooter>
    </Modal>
  );
}

export default Modal;
