import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">{title}</h1>
        {description !== undefined && <p className="mt-1 text-gray-500">{description}</p>}
      </div>
      {actions !== undefined && (
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">{actions}</div>
      )}
    </div>
  );
}

export default PageHeader;
