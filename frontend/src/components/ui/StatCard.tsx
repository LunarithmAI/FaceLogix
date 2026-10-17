import type { ComponentType, SVGProps } from 'react';
import { Card } from '@/components/ui/Card';

type StatTone = 'primary' | 'success' | 'warning' | 'danger' | 'neutral';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  tone?: StatTone;
}

const toneStyles: Record<StatTone, string> = {
  primary: 'bg-primary-50 text-primary-600',
  success: 'bg-green-50 text-green-600',
  warning: 'bg-yellow-50 text-yellow-600',
  danger: 'bg-red-50 text-red-600',
  neutral: 'bg-gray-100 text-gray-600',
};

export function StatCard({ label, value, icon: Icon, tone = 'primary' }: StatCardProps) {
  return (
    <Card padding="sm" className="sm:p-5">
      <div className="flex items-center gap-4">
        <div className={`rounded-lg p-3 ${toneStyles[tone]}`}>
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-gray-500">{label}</p>
          <p className="text-2xl font-bold tabular-nums text-gray-900">{value}</p>
        </div>
      </div>
    </Card>
  );
}

export default StatCard;
