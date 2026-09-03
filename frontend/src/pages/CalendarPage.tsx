import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { calendarApi } from '@/services/calendar';
import type { CalendarExceptionKind } from '@/services/calendar';
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

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary-600">{t('Scheduling')}</p>
        <h1 className="mt-1 text-3xl font-bold text-gray-900">{t('Calendar exceptions')}</h1>
        <p className="mt-2 text-gray-600">{t('Override regular shift weekdays for the organization or one unit.')}</p>
      </header>

      {isAdmin && (
        <Card className="p-5">
          <form className="grid items-end gap-4 md:grid-cols-5" onSubmit={(event) => {
            event.preventDefault();
            if (editingId) editMutation.mutate();
            else createMutation.mutate();
          }}>
            <Input label={t('Exception name')} value={name} onChange={(event) => setName(event.target.value)} required />
            <Input label={t('Date')} type="date" value={exceptionDate} onChange={(event) => setExceptionDate(event.target.value)} required />
            <label className="text-sm font-medium text-gray-700">{t('Kind')}<select value={kind} onChange={(event) => setKind(event.target.value as CalendarExceptionKind)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2"><option value="holiday">{t('Holiday')}</option><option value="working_day">{t('Working day')}</option></select></label>
            <label className="text-sm font-medium text-gray-700">{t('Scope')}<select value={unitId} onChange={(event) => setUnitId(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2"><option value="">{t('Whole organization')}</option>{(unitsQuery.data ?? []).map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select></label>
            <div className="flex gap-2">
              <Button type="submit" isLoading={createMutation.isPending || editMutation.isPending}>{editingId ? t('Save exception') : t('Add exception')}</Button>
              {editingId && <Button type="button" variant="secondary" onClick={resetForm}>{t('Cancel')}</Button>}
            </div>
          </form>
        </Card>
      )}

      {error instanceof Error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error.message}</p>}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500"><tr><th className="px-5 py-3">{t('Date')}</th><th className="px-5 py-3">{t('Name')}</th><th className="px-5 py-3">{t('Kind')}</th><th className="px-5 py-3">{t('Scope')}</th><th className="px-5 py-3 text-right">{t('Actions')}</th></tr></thead>
            <tbody className="divide-y divide-gray-100">
              {(exceptionsQuery.data ?? []).map((exception) => (
                <tr key={exception.id}>
                  <td className="px-5 py-4 font-medium text-gray-900">{exception.exception_date}</td>
                  <td className="px-5 py-4 text-gray-700">{exception.name}</td>
                  <td className="px-5 py-4 text-gray-600">{t(exception.kind === 'holiday' ? 'Holiday' : 'Working day')}</td>
                  <td className="px-5 py-4 text-gray-600">{exception.unit_id ? unitNames.get(exception.unit_id) ?? t('Unit') : t('Whole organization')}</td>
                  <td className="px-5 py-4 text-right">
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
                        <Button type="button" variant="danger" size="sm" onClick={() => deleteMutation.mutate(exception.id)}>{t('Delete')}</Button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!exceptionsQuery.isPending && (exceptionsQuery.data?.length ?? 0) === 0 && <p className="p-8 text-center text-gray-500">{t('No calendar exceptions')}</p>}
      </Card>
    </div>
  );
}

export default CalendarPage;
