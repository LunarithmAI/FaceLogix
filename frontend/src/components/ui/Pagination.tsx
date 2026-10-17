import { Button } from '@/components/ui/Button';
import { translate as t } from '@/i18n';

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  itemLabel: string;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, itemLabel, onPageChange }: PaginationProps) {
  if (pages <= 1) {
    return null;
  }

  return (
    <nav
      aria-label={t('Pagination')}
      className="flex flex-col gap-3 border-t border-gray-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6"
    >
      <p className="text-sm text-gray-500">
        {t('Page')} <span className="font-medium text-gray-900">{page}</span> {t('of')}{' '}
        <span className="font-medium text-gray-900">{pages}</span> ({total} {itemLabel})
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          {t('Previous')}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
        >
          {t('Next')}
        </Button>
      </div>
    </nav>
  );
}

export default Pagination;
