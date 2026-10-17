import type { ReactNode } from 'react';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

type AlertVariant = 'danger' | 'success' | 'warning' | 'info';

interface AlertProps {
  children: ReactNode;
  variant?: AlertVariant;
  className?: string;
}

const variantStyles: Record<AlertVariant, string> = {
  danger: 'border-red-200 bg-red-50 text-red-700',
  success: 'border-green-200 bg-green-50 text-green-700',
  warning: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  info: 'border-blue-200 bg-blue-50 text-blue-700',
};

const variantIcons: Record<AlertVariant, typeof CheckCircleIcon> = {
  danger: XCircleIcon,
  success: CheckCircleIcon,
  warning: ExclamationTriangleIcon,
  info: InformationCircleIcon,
};

export function Alert({ children, variant = 'danger', className = '' }: AlertProps) {
  const Icon = variantIcons[variant];

  return (
    <div
      role={variant === 'danger' ? 'alert' : 'status'}
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${variantStyles[variant]} ${className}`}
    >
      <Icon className="mt-px h-5 w-5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export default Alert;
