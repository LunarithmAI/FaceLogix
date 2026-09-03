import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { usersApi } from '@/services/users';
import type { ShiftSummary } from '@/types/shift';
import type { UnitSummary } from '@/types/unit';
import type { User } from '@/types/user';
import { translate as t } from '@/i18n';

interface UserAssignmentsPanelProps {
  user: User;
  units: UnitSummary[];
  shifts: ShiftSummary[];
  canManageScopes: boolean;
  onUpdated: () => void;
}

export function UserAssignmentsPanel({
  user,
  units,
  shifts,
  canManageScopes,
  onUpdated,
}: UserAssignmentsPanelProps) {
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [effectiveFrom, setEffectiveFrom] = useState(today);
  const [unitId, setUnitId] = useState(user.current_unit?.id ?? '');
  const [shiftId, setShiftId] = useState(user.current_shift?.id ?? '');
  const [managedUnitIds, setManagedUnitIds] = useState(
    user.managed_units.map((unit) => unit.id)
  );
  const unitHistory = useQuery({
    queryKey: ['users', user.id, 'unit-history'],
    queryFn: () => usersApi.getUnitAssignments(user.id),
  });
  const shiftHistory = useQuery({
    queryKey: ['users', user.id, 'shift-history'],
    queryFn: () => usersApi.getShiftAssignments(user.id),
  });
  const unitMutation = useMutation({
    mutationFn: () => usersApi.setUnitAssignment(user.id, unitId || null, effectiveFrom),
    onSuccess: onUpdated,
  });
  const shiftMutation = useMutation({
    mutationFn: () => usersApi.setShiftAssignment(user.id, shiftId || null, effectiveFrom),
    onSuccess: onUpdated,
  });
  const activationMutation = useMutation({
    mutationFn: () => usersApi.activate(user.id, unitId, shiftId || undefined),
    onSuccess: onUpdated,
  });
  const scopeMutation = useMutation({
    mutationFn: () => usersApi.setManagedUnits(user.id, managedUnitIds),
    onSuccess: onUpdated,
  });
  const error =
    unitMutation.error ??
    shiftMutation.error ??
    scopeMutation.error ??
    activationMutation.error;

  return (
    <div className="mt-6 border-t border-gray-200 pt-6">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-900">
        {t('Effective-dated assignments')}
      </h3>
      {error instanceof Error && (
        <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error.message}
        </p>
      )}
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-medium text-gray-700">
          {t('Effective from')}
          <input type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2" />
        </label>
        <label className="text-sm font-medium text-gray-700">
          {t('Unit')}
          <select value={unitId} onChange={(event) => setUnitId(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2">
            <option value="">{t('Not assigned')}</option>
            {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
          </select>
          {user.is_active && <Button type="button" size="sm" className="mt-2" onClick={() => unitMutation.mutate()} isLoading={unitMutation.isPending}>{t('Apply unit')}</Button>}
        </label>
        <label className="text-sm font-medium text-gray-700">
          {t('Shift')}
          <select value={shiftId} onChange={(event) => setShiftId(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2">
            <option value="">{t('Not assigned')}</option>
            {shifts.map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}
          </select>
          {user.is_active && <Button type="button" size="sm" className="mt-2" onClick={() => shiftMutation.mutate()} isLoading={shiftMutation.isPending}>{t('Apply shift')}</Button>}
        </label>
      </div>
      {!user.is_active && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-sm text-amber-900">{t('Activation requires an assigned unit.')}</p>
          <Button
            type="button"
            size="sm"
            className="mt-3"
            disabled={!unitId}
            onClick={() => activationMutation.mutate()}
            isLoading={activationMutation.isPending}
          >
            {t('Activate user')}
          </Button>
        </div>
      )}

      <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <h4 className="font-semibold text-gray-800">{t('Unit history')}</h4>
          <ul className="mt-2 space-y-1 text-gray-600">
            {(unitHistory.data ?? []).map((entry) => (
              <li key={entry.id}>{entry.unit.name}: {entry.effective_from} — {entry.effective_to ?? t('Present')}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-gray-800">{t('Shift history')}</h4>
          <ul className="mt-2 space-y-1 text-gray-600">
            {(shiftHistory.data ?? []).map((entry) => (
              <li key={entry.id}>{entry.shift.name}: {entry.effective_from} — {entry.effective_to ?? t('Present')}</li>
            ))}
          </ul>
        </div>
      </div>

      {canManageScopes && user.role === 'manager' && (
        <div className="mt-6 border-t border-gray-200 pt-5">
          <h4 className="font-semibold text-gray-800">{t('Managed units')}</h4>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {units.map((unit) => (
              <label key={unit.id} className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={managedUnitIds.includes(unit.id)}
                  onChange={(event) => setManagedUnitIds((current) =>
                    event.target.checked
                      ? [...current, unit.id]
                      : current.filter((id) => id !== unit.id)
                  )}
                />
                {unit.name}
              </label>
            ))}
          </div>
          <Button type="button" size="sm" className="mt-3" onClick={() => scopeMutation.mutate()} isLoading={scopeMutation.isPending}>{t('Save managed units')}</Button>
        </div>
      )}
    </div>
  );
}
