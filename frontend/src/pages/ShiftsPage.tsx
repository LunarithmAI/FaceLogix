import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { shiftsApi } from '@/services/shifts';
import { unitsApi } from '@/services/units';
import { useAuthStore } from '@/stores/authStore';
import { ADMIN_ROLES } from '@/types/roles';
import { translate as t } from '@/i18n';

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export function ShiftsPage() {
  const queryClient = useQueryClient();
  const session = useAuthStore((state) => state.session);
  const isAdmin = session?.kind === 'user' && ADMIN_ROLES.includes(session.user.role);
  const [name, setName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');
  const [lateGrace, setLateGrace] = useState(15);
  const [earlyGrace, setEarlyGrace] = useState(0);
  const [weekdays, setWeekdays] = useState([0, 1, 2, 3, 4]);
  const [unitId, setUnitId] = useState('');
  const [shiftId, setShiftId] = useState('');
  const [effectiveFrom, setEffectiveFrom] = useState(new Date().toISOString().slice(0, 10));
  const shiftsQuery = useQuery({ queryKey: ['shifts', isAdmin ? 'all' : 'active'], queryFn: ({ signal }) => shiftsApi.list(isAdmin, signal) });
  const unitsQuery = useQuery({ queryKey: ['units', 'active'], queryFn: ({ signal }) => unitsApi.list(false, signal) });
  const resetBuilder = () => {
    setEditingId(null);
    setName('');
    setStartTime('09:00');
    setEndTime('17:00');
    setLateGrace(15);
    setEarlyGrace(0);
    setWeekdays([0, 1, 2, 3, 4]);
  };
  const shiftPayload = () => ({
    name,
    start_time: startTime,
    end_time: endTime,
    late_grace_minutes: lateGrace,
    early_departure_grace_minutes: earlyGrace,
    scheduled_weekdays: weekdays,
  });
  const createMutation = useMutation({
    mutationFn: () => shiftsApi.create(shiftPayload()),
    onSuccess: async () => {
      resetBuilder();
      await queryClient.invalidateQueries({ queryKey: ['shifts'] });
    },
  });
  const editMutation = useMutation({
    mutationFn: () => shiftsApi.update(editingId!, shiftPayload()),
    onSuccess: async () => {
      resetBuilder();
      await queryClient.invalidateQueries({ queryKey: ['shifts'] });
    },
  });
  const archiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => shiftsApi.update(id, { is_active: active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shifts'] }),
  });
  const assignMutation = useMutation({ mutationFn: () => shiftsApi.assignUnit(unitId, shiftId || null, effectiveFrom) });
  const error =
    createMutation.error ??
    editMutation.error ??
    archiveMutation.error ??
    assignMutation.error ??
    shiftsQuery.error;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary-600">{t('Scheduling')}</p>
        <h1 className="mt-1 text-3xl font-bold text-gray-900">{t('Shifts')}</h1>
        <p className="mt-2 text-gray-600">{t('Define attendance windows, grace periods, and scheduled weekdays.')}</p>
      </header>

      {isAdmin && (
        <Card className="p-5">
          <form className="space-y-4" onSubmit={(event) => {
            event.preventDefault();
            if (editingId) editMutation.mutate();
            else createMutation.mutate();
          }}>
            <div className="grid gap-4 md:grid-cols-5">
              <Input label={t('Shift name')} value={name} onChange={(event) => setName(event.target.value)} required />
              <Input label={t('Start Time')} type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
              <Input label={t('End Time')} type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} required />
              <Input label={t('Late grace')} type="number" min={0} value={lateGrace} onChange={(event) => setLateGrace(Number(event.target.value))} />
              <Input label={t('Early departure grace')} type="number" min={0} value={earlyGrace} onChange={(event) => setEarlyGrace(Number(event.target.value))} />
            </div>
            <fieldset>
              <legend className="text-sm font-medium text-gray-700">{t('Scheduled weekdays')}</legend>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
                {WEEKDAYS.map((day, index) => (
                  <label key={day} className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" checked={weekdays.includes(index)} onChange={(event) => setWeekdays((current) => event.target.checked ? [...current, index].sort() : current.filter((value) => value !== index))} />
                    {t(day)}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="flex gap-2">
              <Button type="submit" isLoading={createMutation.isPending || editMutation.isPending}>{editingId ? t('Save shift') : t('Add shift')}</Button>
              {editingId && <Button type="button" variant="secondary" onClick={resetBuilder}>{t('Cancel')}</Button>}
            </div>
          </form>
        </Card>
      )}

      {error instanceof Error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error.message}</p>}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500"><tr><th className="px-5 py-3">{t('Shift')}</th><th className="px-5 py-3">{t('Window')}</th><th className="px-5 py-3">{t('Weekdays')}</th><th className="px-5 py-3">{t('Status')}</th><th className="px-5 py-3 text-right">{t('Actions')}</th></tr></thead>
            <tbody className="divide-y divide-gray-100">
              {(shiftsQuery.data ?? []).map((shift) => (
                <tr key={shift.id}>
                  <td className="px-5 py-4 font-medium text-gray-900">{shift.name}</td>
                  <td className="px-5 py-4 text-gray-600">{shift.start_time.slice(0, 5)}–{shift.end_time.slice(0, 5)}</td>
                  <td className="px-5 py-4 text-gray-600">{shift.scheduled_weekdays.map((day) => t(WEEKDAYS[day])).join(', ')}</td>
                  <td className="px-5 py-4 text-gray-600">{shift.is_active ? t('Active') : t('Archived')}</td>
                  <td className="px-5 py-4 text-right">
                    {isAdmin && (
                      <span className="inline-flex gap-2">
                        <Button type="button" variant="secondary" size="sm" onClick={() => {
                          setEditingId(shift.id);
                          setName(shift.name);
                          setStartTime(shift.start_time.slice(0, 5));
                          setEndTime(shift.end_time.slice(0, 5));
                          setLateGrace(shift.late_grace_minutes);
                          setEarlyGrace(shift.early_departure_grace_minutes);
                          setWeekdays(shift.scheduled_weekdays);
                          window.scrollTo({ top: 0 });
                        }}>{t('Edit')}</Button>
                        <Button type="button" variant="secondary" size="sm" onClick={() => archiveMutation.mutate({ id: shift.id, active: !shift.is_active })}>{shift.is_active ? t('Archive') : t('Restore')}</Button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {isAdmin && (
        <Card className="p-5">
          <h2 className="text-lg font-semibold text-gray-900">{t('Assign a shift to a unit')}</h2>
          <div className="mt-4 grid items-end gap-4 sm:grid-cols-4">
            <label className="text-sm font-medium text-gray-700">{t('Unit')}<select value={unitId} onChange={(event) => setUnitId(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2"><option value="">{t('Select unit')}</option>{(unitsQuery.data ?? []).map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select></label>
            <label className="text-sm font-medium text-gray-700">{t('Shift')}<select value={shiftId} onChange={(event) => setShiftId(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2"><option value="">{t('Clear assignment')}</option>{(shiftsQuery.data ?? []).filter((shift) => shift.is_active).map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}</select></label>
            <Input label={t('Effective from')} type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} />
            <Button type="button" disabled={!unitId} onClick={() => assignMutation.mutate()} isLoading={assignMutation.isPending}>{t('Apply to unit')}</Button>
          </div>
        </Card>
      )}
    </div>
  );
}

export default ShiftsPage;
