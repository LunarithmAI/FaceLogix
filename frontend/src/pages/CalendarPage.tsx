import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ConfirmModal } from '@/components/ui/Modal';
import { PageHeader } from '@/components/ui/PageHeader';
import { Select } from '@/components/ui/Select';
import { calendarApi } from '@/services/calendar';
import type { CalendarException, CalendarExceptionKind } from '@/services/calendar';
import { unitsApi } from '@/services/units';
import { useAuthStore } from '@/stores/authStore';
import { ADMIN_ROLES } from '@/types/roles';
import { translate as t } from '@/i18n';

export function CalendarPage() {
  const queryClient = useQueryClient();
  const session = useAuthStore((state) => state.session);
  const isAdmin = session?.kind === 'user' && ADMIN_ROLES.includes(session.user.role);
  const [name, setName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [exceptionDate, setExceptionDate] = useState(new Date().toISOString().slice(0, 10));
  const [kind, setKind] = useState<CalendarExceptionKind>('holiday');
  const [unitId, setUnitId] = useState('');
  const [pendingDelete, setPendingDelete] = useState<CalendarException | null>(null);
  const exceptionsQuery = useQuery({ queryKey: ['calendar-exceptions'], queryFn: ({ signal }) => calendarApi.list(undefined, undefined, signal) });
  const unitsQuery = useQuery({ queryKey: ['units', 'active'], queryFn: ({ signal }) => unitsApi.list(false, signal) });
  const resetForm = () => {
    setEditingId(null);
    setName('');
    setExceptionDate(new Date().toISOString().slice(0, 10));
    setKind('holiday');
    setUnitId('');
  };
  const payload = () => ({
    name,
    exception_date: exceptionDate,
    kind,
    unit_id: unitId || null,
  });
  const createMutation = useMutation({
    mutationFn: () => calendarApi.create(payload()),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ['calendar-exceptions'] });
    },
  });
  const editMutation = useMutation({
    mutationFn: () => calendarApi.update(editingId!, payload()),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ['calendar-exceptions'] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => calendarApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['calendar-exceptions'] }),
  });
  const error =
    createMutation.error ?? editMutation.error ?? deleteMutation.error ?? exceptionsQuery.error;
  const unitNames = new Map((unitsQuery.data ?? []).map((unit) => [unit.id, unit.name]));

  const exceptions = exceptionsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('Calendar exceptions')}
        description={t('Override regular shift weekdays for the organization or one unit.')}
      />

      {isAdmin && (
        <Card>
          <form className="grid items-end gap-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={(event) => {
            event.preventDefault();
            if (editingId) editMutation.mutate();
            else createMutation.mutate();
          }}>
            <Input label={t('Exception name')} value={name} onChange={(event) => setName(event.target.value)} required />
            <Input label={t('Date')} type="date" value={exceptionDate} onChange={(event) => setExceptionDate(event.target.value)} required />
            <Select label={t('Kind')} value={kind} onChange={(event) => setKind(event.target.value as CalendarExceptionKind)}>
              <option value="holiday">{t('Holiday')}</option>
              <option value="working_day">{t('Working day')}</option>
            </Select>
            <Select label={t('Scope')} value={unitId} onChange={(event) => setUnitId(event.target.value)}>
              <option value="">{t('Whole organization')}</option>
              {(unitsQuery.data ?? []).map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
            </Select>
            <div className="flex gap-2">
              <Button type="submit" className="flex-1" isLoading={createMutation.isPending || editMutation.isPending}>{editingId ? t('Save exception') : t('Add exception')}</Button>
              {editingId && <Button type="button" variant="secondary" onClick={resetForm}>{t('Cancel')}</Button>}
            </div>
          </form>
        </Card>
      )}

      {error instanceof Error && <Alert>{t(error.message)}</Alert>}

      <Card padding="none" className="overflow-hidden">
        {exceptionsQuery.isPending ? (
          <div className="py-12">
            <Loading size="lg" text={t('Loading calendar exceptions...')} />
          </div>
        ) : exceptions.length === 0 ? (
          <p className="py-12 text-center text-gray-500">{t('No calendar exceptions')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wider text-gray-500 [&_th]:font-medium">
                <tr>
                  <th className="px-6 py-3">{t('Date')}</th>
                  <th className="px-6 py-3">{t('Name')}</th>
                  <th className="px-6 py-3">{t('Kind')}</th>
                  <th className="px-6 py-3">{t('Scope')}</th>
                  <th className="px-6 py-3 text-right">{t('Actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {exceptions.map((exception) => (
                  <tr key={exception.id} className={editingId === exception.id ? 'bg-primary-50' : 'hover:bg-gray-50'}>
                    <td className="whitespace-nowrap px-6 py-3 font-medium tabular-nums text-gray-900">{exception.exception_date}</td>
                    <td className="px-6 py-3 text-gray-700">{exception.name}</td>
                    <td className="px-6 py-3">
                      <Badge variant={exception.kind === 'holiday' ? 'warning' : 'info'}>
                        {t(exception.kind === 'holiday' ? 'Holiday' : 'Working day')}
                      </Badge>
                    </td>
                    <td className="px-6 py-3 text-gray-600">{exception.unit_id ? unitNames.get(exception.unit_id) ?? t('Unit') : t('Whole organization')}</td>
                    <td className="whitespace-nowrap px-6 py-3 text-right">
                      {isAdmin && (
                        <span className="inline-flex gap-2">
                          <Button type="button" variant="secondary" size="sm" onClick={() => {
                            setEditingId(exception.id);
                            setName(exception.name);
                            setExceptionDate(exception.exception_date);
                            setKind(exception.kind);
                            setUnitId(exception.unit_id ?? '');
                            window.scrollTo({ top: 0 });
                          }}>{t('Edit')}</Button>
                          <Button type="button" variant="ghost" size="sm" className="text-red-600 hover:bg-red-50" onClick={() => setPendingDelete(exception)}>{t('Delete')}</Button>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmModal
        isOpen={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete !== null) {
            deleteMutation.mutate(pendingDelete.id, { onSettled: () => setPendingDelete(null) });
          }
        }}
        title={t('Delete exception')}
        message={t('Delete {{name}} on {{date}}? This action cannot be undone.', {
          name: pendingDelete?.name,
          date: pendingDelete?.exception_date,
        })}
        confirmText={t('Delete')}
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}

export default CalendarPage;
