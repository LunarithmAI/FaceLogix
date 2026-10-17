import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PlusIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { PageHeader } from '@/components/ui/PageHeader';
import { Select } from '@/components/ui/Select';
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

  const units = unitsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('Units')}
        description={t('Departments and classes used for access scope, assignments, and reports.')}
      />

      {isAdmin && (
        <Card>
          <form
            className="grid items-end gap-4 sm:grid-cols-[1fr_14rem_auto]"
            onSubmit={(event) => {
              event.preventDefault();
              createMutation.mutate();
            }}
          >
            <Input label={t('Unit name')} value={name} onChange={(event) => setName(event.target.value)} required />
            <Select label={t('Unit kind')} value={kind} onChange={(event) => setKind(event.target.value as UnitKind)}>
              <option value="department">{t('Department')}</option>
              <option value="class">{t('Class')}</option>
            </Select>
            <Button
              type="submit"
              isLoading={createMutation.isPending}
              leftIcon={<PlusIcon className="h-5 w-5" aria-hidden="true" />}
            >
              {t('Add unit')}
            </Button>
          </form>
        </Card>
      )}

      {error instanceof Error && <Alert>{t(error.message)}</Alert>}

      <Card padding="none" className="overflow-hidden">
        {unitsQuery.isPending ? (
          <div className="py-12">
            <Loading size="lg" text={t('Loading units...')} />
          </div>
        ) : units.length === 0 ? (
          <p className="py-12 text-center text-gray-500">{t('No units yet')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wider text-gray-500 [&_th]:font-medium">
                <tr>
                  <th className="px-6 py-3">{t('Name')}</th>
                  <th className="px-6 py-3">{t('Kind')}</th>
                  <th className="px-6 py-3">{t('Status')}</th>
                  <th className="px-6 py-3 text-right">{t('Actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {units.map((unit) => (
                  <tr key={unit.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium text-gray-900">
                      {editingId === unit.id ? (
                        <Input aria-label={t('Unit name')} value={editName} onChange={(event) => setEditName(event.target.value)} />
                      ) : (
                        unit.name
                      )}
                    </td>
                    <td className="px-6 py-3 text-gray-600">
                      {editingId === unit.id ? (
                        <Select aria-label={t('Unit kind')} value={editKind} onChange={(event) => setEditKind(event.target.value as UnitKind)}>
                          <option value="department">{t('Department')}</option>
                          <option value="class">{t('Class')}</option>
                        </Select>
                      ) : (
                        t(unit.kind === 'department' ? 'Department' : 'Class')
                      )}
                    </td>
                    <td className="px-6 py-3">
                      <Badge variant={unit.is_active ? 'success' : 'default'} dot>
                        {unit.is_active ? t('Active') : t('Archived')}
                      </Badge>
                    </td>
                    <td className="whitespace-nowrap px-6 py-3 text-right">
                      {isAdmin && editingId === unit.id && (
                        <span className="inline-flex gap-2">
                          <Button type="button" size="sm" onClick={() => editMutation.mutate()} isLoading={editMutation.isPending}>{t('Save')}</Button>
                          <Button type="button" variant="secondary" size="sm" onClick={() => setEditingId(null)}>{t('Cancel')}</Button>
                        </span>
                      )}
                      {isAdmin && editingId !== unit.id && (
                        <span className="inline-flex gap-2">
                          <Button type="button" variant="secondary" size="sm" onClick={() => { setEditingId(unit.id); setEditName(unit.name); setEditKind(unit.kind); }}>{t('Edit')}</Button>
                          <Button type="button" variant="ghost" size="sm" onClick={() => archiveMutation.mutate({ id: unit.id, isActive: !unit.is_active })}>{unit.is_active ? t('Archive') : t('Restore')}</Button>
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
    </div>
  );
}

export default UnitsPage;
