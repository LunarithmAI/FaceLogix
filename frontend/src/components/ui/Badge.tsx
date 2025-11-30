import { ReactNode } from 'react';

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
type BadgeSize = 'sm' | 'md' | 'lg';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-700',
  primary: 'bg-primary-100 text-primary-700',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-yellow-100 text-yellow-700',
  danger: 'bg-red-100 text-red-700',
  info: 'bg-blue-100 text-blue-700',
};

const dotVariantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-400',
  primary: 'bg-primary-500',
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1 text-sm',
};

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  dot = false,
  className = '',
}: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${className}
      `}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dotVariantStyles[variant]}`}
        />
      )}
      {children}
    </span>
  );
}

// Status-specific badges for common use cases
export function StatusBadge({ status }: { status: 'active' | 'inactive' | 'pending' }) {
  const config = {
    active: { variant: 'success' as const, label: 'Active' },
    inactive: { variant: 'danger' as const, label: 'Inactive' },
    pending: { variant: 'warning' as const, label: 'Pending' },
  };

  const { variant, label } = config[status];

  return (
    <Badge variant={variant} dot>
      {label}
    </Badge>
  );
}

export function RoleBadge({ role }: { role: 'admin' | 'manager' | 'employee' }) {
  const config = {
    admin: { variant: 'danger' as const, label: 'Admin' },
    manager: { variant: 'primary' as const, label: 'Manager' },
    employee: { variant: 'default' as const, label: 'Employee' },
  };

  const { variant, label } = config[role];

  return <Badge variant={variant}>{label}</Badge>;
}

export default Badge;
