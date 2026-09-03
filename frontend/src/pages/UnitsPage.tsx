import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { unitsApi } from '@/services/units';
import { useAuthStore } from '@/stores/authStore';
import { ADMIN_ROLES } from '@/types/roles';
import type { UnitKind } from '@/types/unit';
import { translate as t } from '@/i18n';

export function UnitsPage() {
  const queryClient = useQueryClient();
  const session = useAuthStore((state) => state.session);
  const isAdmin = session?.kind === 'user' && ADMIN_ROLES.includes(session.user.role);
  const [name, setName] = useState('');
  const [kind, setKind] = useState<UnitKind>('department');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editKind, setEditKind] = useState<UnitKind>('department');
  const unitsQuery = useQuery({
    queryKey: ['units', isAdmin ? 'all' : 'active'],
    queryFn: ({ signal }) => unitsApi.list(isAdmin, signal),
  });
  const createMutation = useMutation({
    mutationFn: () => unitsApi.create({ name, kind }),
    onSuccess: async () => {
      setName('');
      await queryClient.invalidateQueries({ queryKey: ['units'] });
    },
  });
  const archiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      unitsApi.update(id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['units'] }),
  });
  const editMutation = useMutation({
    mutationFn: () => unitsApi.update(editingId!, { name: editName, kind: editKind }),
    onSuccess: async () => {
      setEditingId(null);
      await queryClient.invalidateQueries({ queryKey: ['units'] });
    },
  });
  const error =
    createMutation.error ?? editMutation.error ?? archiveMutation.error ?? unitsQuery.error;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary-600">{t('Organization')}</p>
        <h1 className="mt-1 text-3xl font-bold text-gray-900">{t('Units')}</h1>
        <p className="mt-2 text-gray-600">{t('Departments and classes used for access scope, assignments, and reports.')}</p>
      </header>

      {isAdmin && (
        <Card className="p-5">
          <form className="grid items-end gap-4 sm:grid-cols-[1fr_14rem_auto]" onSubmit={(event) => { event.preventDefault(); createMutation.mutate(); }}>
            <Input label={t('Unit name')} value={name} onChange={(event) => setName(event.target.value)} required />
            <label className="text-sm font-medium text-gray-700">
              {t('Unit kind')}
              <select value={kind} onChange={(event) => setKind(event.target.value as UnitKind)} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2">
                <option value="department">{t('Department')}</option>
                <option value="class">{t('Class')}</option>
              </select>
            </label>
            <Button type="submit" isLoading={createMutation.isPending}>{t('Add unit')}</Button>
          </form>
        </Card>
      )}

      {error instanceof Error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error.message}</p>}

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr><th className="px-5 py-3">{t('Name')}</th><th className="px-5 py-3">{t('Kind')}</th><th className="px-5 py-3">{t('Status')}</th><th className="px-5 py-3 text-right">{t('Actions')}</th></tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(unitsQuery.data ?? []).map((unit) => (
                <tr key={unit.id}>
                  <td className="px-5 py-4 font-medium text-gray-900">
                    {editingId === unit.id ? <input aria-label={t('Unit name')} value={editName} onChange={(event) => setEditName(event.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2" /> : unit.name}
                  </td>
                  <td className="px-5 py-4 text-gray-600">
                    {editingId === unit.id ? (
                      <select aria-label={t('Unit kind')} value={editKind} onChange={(event) => setEditKind(event.target.value as UnitKind)} className="rounded-lg border border-gray-300 bg-white px-3 py-2">
                        <option value="department">{t('Department')}</option>
                        <option value="class">{t('Class')}</option>
                      </select>
                    ) : t(unit.kind === 'department' ? 'Department' : 'Class')}
                  </td>
                  <td className="px-5 py-4 text-gray-600">{unit.is_active ? t('Active') : t('Archived')}</td>
                  <td className="px-5 py-4 text-right">
                    {isAdmin && editingId === unit.id && (
                      <span className="inline-flex gap-2">
                        <Button type="button" size="sm" onClick={() => editMutation.mutate()} isLoading={editMutation.isPending}>{t('Save')}</Button>
                        <Button type="button" variant="secondary" size="sm" onClick={() => setEditingId(null)}>{t('Cancel')}</Button>
                      </span>
                    )}
                    {isAdmin && editingId !== unit.id && (
                      <span className="inline-flex gap-2">
                        <Button type="button" variant="secondary" size="sm" onClick={() => { setEditingId(unit.id); setEditName(unit.name); setEditKind(unit.kind); }}>{t('Edit')}</Button>
                        <Button type="button" variant="secondary" size="sm" onClick={() => archiveMutation.mutate({ id: unit.id, isActive: !unit.is_active })}>{unit.is_active ? t('Archive') : t('Restore')}</Button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!unitsQuery.isPending && (unitsQuery.data?.length ?? 0) === 0 && <p className="p-8 text-center text-gray-500">{t('No units yet')}</p>}
      </Card>
    </div>
  );
}

export default UnitsPage;
