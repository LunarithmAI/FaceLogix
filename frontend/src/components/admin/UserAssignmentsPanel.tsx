import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
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
      {error instanceof Error && <Alert className="mt-3">{t(error.message)}</Alert>}
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Input label={t('Effective from')} type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} />
        <div>
          <Select label={t('Unit')} value={unitId} onChange={(event) => setUnitId(event.target.value)}>
            <option value="">{t('Not assigned')}</option>
            {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
          </Select>
          {user.is_active && <Button type="button" size="sm" variant="secondary" className="mt-2" onClick={() => unitMutation.mutate()} isLoading={unitMutation.isPending}>{t('Apply unit')}</Button>}
        </div>
        <div>
          <Select label={t('Shift')} value={shiftId} onChange={(event) => setShiftId(event.target.value)}>
            <option value="">{t('Not assigned')}</option>
            {shifts.map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}
          </Select>
          {user.is_active && <Button type="button" size="sm" variant="secondary" className="mt-2" onClick={() => shiftMutation.mutate()} isLoading={shiftMutation.isPending}>{t('Apply shift')}</Button>}
        </div>
      </div>
      {!user.is_active && (
        <div className="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3">
          <p className="text-sm text-yellow-800">{t('Activation requires an assigned unit.')}</p>
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
              <label key={unit.id} className="flex min-h-11 items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-primary-600"
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
