import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { PlusIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal, ConfirmModal, ModalFooter } from '@/components/ui/Modal';
import { DeviceTable } from '@/components/admin/DeviceTable';
import { Loading } from '@/components/ui/Loading';
import { Alert } from '@/components/ui/Alert';
import { PageHeader } from '@/components/ui/PageHeader';
import { Pagination } from '@/components/ui/Pagination';
import { Select } from '@/components/ui/Select';
import { devicesApi } from '@/services/devices';
import type {
  Device,
  DeviceCredential,
  DeviceMode,
  DeviceRegistration,
  DeviceSettings,
  DeviceType,
} from '@/types/device';
import { queryClient, queryKeys } from '@/lib/queryClient';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { translate as t } from '@/i18n';

const DEFAULT_DEVICE_SETTINGS: DeviceSettings = {
  allow_check_in: true,
  allow_check_out: true,
  default_mode: 'check_in',
  camera_facing: 'user',
};

export function DevicesPage() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search);
  const [page, setPage] = useState(1);

  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isRegenerateOpen, setIsRegenerateOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [newCredential, setNewCredential] = useState<DeviceCredential | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    device_type: 'kiosk' as DeviceType,
    location: '',
    settings: { ...DEFAULT_DEVICE_SETTINGS },
  });

  const devicesQuery = useQuery({
    queryKey: queryKeys.devices({
      page,
      page_size: 10,
      search: debouncedSearch || undefined,
    }),
    queryFn: ({ signal }) =>
      devicesApi.list(
        {
          page,
          page_size: 10,
          search: debouncedSearch || undefined,
        },
        signal
      ),
    placeholderData: keepPreviousData,
  });
  const saveMutation = useMutation({
    mutationFn: async (input: { deviceId?: string; data: DeviceRegistration }) => {
      if (input.deviceId !== undefined) {
        await devicesApi.update(input.deviceId, {
          name: input.data.name,
          device_type: input.data.device_type,
          location: input.data.location,
        });
        const device = await devicesApi.updateSettings(
          input.deviceId,
          input.data.settings ?? DEFAULT_DEVICE_SETTINGS
        );
        return { kind: 'updated' as const, device };
      }
      const device = await devicesApi.register(input.data);
      return { kind: 'created' as const, device };
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (deviceId: string) => devicesApi.delete(deviceId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
  const toggleMutation = useMutation({
    mutationFn: (device: Device) =>
      device.is_active ? devicesApi.deactivate(device.id) : devicesApi.activate(device.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
  const regenerateMutation = useMutation({
    mutationFn: (deviceId: string) => devicesApi.regenerateSecret(deviceId),
    onSuccess: async (credential) => {
      setIsRegenerateOpen(false);
      setNewCredential(credential);
      await queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });
  const devices = devicesQuery.data;
  const isSubmitting =
    saveMutation.isPending || deleteMutation.isPending || regenerateMutation.isPending;
  const actionError =
    saveMutation.error ?? deleteMutation.error ?? toggleMutation.error ?? regenerateMutation.error;

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleCreate = () => {
    setSelectedDevice(null);
    setSettingsError(null);
    setFormData({
      name: '',
      device_type: 'kiosk',
      location: '',
      settings: { ...DEFAULT_DEVICE_SETTINGS },
    });
    setIsFormOpen(true);
  };

  const handleEdit = (device: Device) => {
    setSelectedDevice(device);
    setSettingsError(null);
    setFormData({
      name: device.name,
      device_type: device.device_type,
      location: device.location || '',
      settings: { ...device.settings },
    });
    setIsFormOpen(true);
  };

  const handleDelete = (device: Device) => {
    setSelectedDevice(device);
    setIsDeleteOpen(true);
  };

  const handleToggleStatus = (device: Device) => {
    toggleMutation.mutate(device);
  };

  const handleRegenerateSecret = (device: Device) => {
    setSelectedDevice(device);
    setIsRegenerateOpen(true);
  };

  const setActionEnabled = (
    action: 'allow_check_in' | 'allow_check_out',
    enabled: boolean
  ) => {
    const settings = { ...formData.settings, [action]: enabled };
    if (settings.allow_check_in !== settings.allow_check_out) {
      settings.default_mode = settings.allow_check_in ? 'check_in' : 'check_out';
    }
    setFormData({ ...formData, settings });
  };

  const handleFormSubmit = () => {
    const { settings } = formData;
    if (
      (settings.allow_check_in || settings.allow_check_out) &&
      ((settings.default_mode === 'check_in' && !settings.allow_check_in) ||
        (settings.default_mode === 'check_out' && !settings.allow_check_out))
    ) {
      setSettingsError(t('Default mode must be enabled'));
      return;
    }
    setSettingsError(null);
    const data: DeviceRegistration = {
      name: formData.name,
      device_type: formData.device_type,
      location: formData.location || undefined,
      settings,
    };
    saveMutation.mutate(
      {
        deviceId: selectedDevice?.id,
        data,
      },
      {
        onSuccess: (result) => {
          setIsFormOpen(false);
          if (result.kind === 'created') {
            setNewCredential(result.device);
          }
        },
      }
    );
  };

  const handleConfirmDelete = () => {
    if (selectedDevice === null) {
      return;
    }
    deleteMutation.mutate(selectedDevice.id, {
      onSuccess: () => setIsDeleteOpen(false),
    });
  };

  const handleConfirmRegenerate = () => {
    if (selectedDevice !== null) {
      regenerateMutation.mutate(selectedDevice.id);
    }
  };

  return (
    <>
      <div className="space-y-6">
        <PageHeader
          title={t('Devices')}
          description={t('Manage check-in devices and kiosks')}
          actions={
            <Button
              leftIcon={<PlusIcon className="h-5 w-5" aria-hidden="true" />}
              onClick={handleCreate}
            >
              {t('Add Device')}
            </Button>
          }
        />

        {actionError !== null && <Alert>{t(actionError.message)}</Alert>}

        <Card padding="none" className="overflow-hidden">
          <div className="border-b border-gray-200 p-4 sm:px-6">
            <div className="relative max-w-md">
              <MagnifyingGlassIcon
                className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400"
                aria-hidden="true"
              />
              <Input
                type="search"
                aria-label={t('Search devices')}
                placeholder={t('Search devices...')}
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {devicesQuery.isPending ? (
            <div className="py-12">
              <Loading size="lg" text={t('Loading devices...')} />
            </div>
          ) : devicesQuery.error !== null ? (
            <div className="p-6 text-center text-red-700" role="alert">
              <p>{t(devicesQuery.error.message)}</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => void devicesQuery.refetch()}
              >
                {t('Try again')}
              </Button>
            </div>
          ) : (
            <>
              <DeviceTable
                devices={devices?.items || []}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onToggleStatus={handleToggleStatus}
                onRegenerateSecret={handleRegenerateSecret}
              />
              {devices && (
                <Pagination
                  page={devices.page}
                  pages={devices.pages}
                  total={devices.total}
                  itemLabel={t('devices')}
                  onPageChange={setPage}
                />
              )}
            </>
          )}
        </Card>
      </div>

      {/* Device Form Modal */}
      <Modal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        title={selectedDevice ? t('Edit Device') : t('Register Device')}
      >
        <div className="space-y-4">
          {saveMutation.error !== null && <Alert>{t(saveMutation.error.message)}</Alert>}
          <Input
            label={t('Device Name')}
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder={t('Main Entrance Kiosk')}
            required
          />

          <Select
            id="device-type"
            label={t('Device Type')}
            value={formData.device_type}
            onChange={(e) =>
              setFormData({ ...formData, device_type: e.target.value as DeviceType })
            }
          >
            <option value="kiosk">{t('Kiosk')}</option>
            <option value="tablet">{t('Tablet')}</option>
            <option value="mobile">{t('Mobile')}</option>
            <option value="web">{t('Web')}</option>
          </Select>

          <Input
            label={t('Location')}
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            placeholder={t('Building A, Floor 1')}
          />

          <fieldset className="space-y-1 rounded-lg border border-gray-200 px-4 pb-3 pt-2">
            <legend className="px-1 text-sm font-semibold text-gray-900">
              {t('Kiosk actions')}
            </legend>
            <label className="flex min-h-11 items-center gap-3 text-sm text-gray-800">
              <input
                type="checkbox"
                checked={formData.settings.allow_check_in}
                onChange={(event) => setActionEnabled('allow_check_in', event.target.checked)}
                className="h-5 w-5 rounded border-gray-300 accent-primary-600"
              />
              {t('Allow check-in')}
            </label>
            <label className="flex min-h-11 items-center gap-3 text-sm text-gray-800">
              <input
                type="checkbox"
                checked={formData.settings.allow_check_out}
                onChange={(event) => setActionEnabled('allow_check_out', event.target.checked)}
                className="h-5 w-5 rounded border-gray-300 accent-primary-600"
              />
              {t('Allow check-out')}
            </label>
            {!formData.settings.allow_check_in && !formData.settings.allow_check_out && (
              <Alert variant="warning">
                {t('This kiosk will be blocked until an action is enabled.')}
              </Alert>
            )}
          </fieldset>

          <Select
            id="default-mode"
            label={t('Default mode')}
            value={formData.settings.default_mode}
            onChange={(event) =>
              setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  default_mode: event.target.value as DeviceMode,
                },
              })
            }
          >
            <option value="check_in">{t('Check In')}</option>
            <option value="check_out">{t('Check Out')}</option>
          </Select>

          <Select
            id="camera-facing"
            label={t('Camera facing')}
            value={formData.settings.camera_facing}
            onChange={(event) =>
              setFormData({
                ...formData,
                settings: {
                  ...formData.settings,
                  camera_facing: event.target.value as 'user' | 'environment',
                },
              })
            }
          >
            <option value="user">{t('Front camera')}</option>
            <option value="environment">{t('Rear camera')}</option>
          </Select>

          {settingsError !== null && <Alert>{settingsError}</Alert>}
        </div>

        <ModalFooter>
          <Button variant="secondary" onClick={() => setIsFormOpen(false)}>
            {t('Cancel')}
          </Button>
          <Button onClick={handleFormSubmit} isLoading={isSubmitting}>
            {selectedDevice ? t('Update') : t('Register')}
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        isOpen={newCredential !== null}
        onClose={() => setNewCredential(null)}
        title={t('Save device credentials')}
      >
        <p className="text-sm text-gray-600">
          {t('This secret is shown once. Store it in the device configuration before closing.')}
        </p>
        <dl className="mt-4 space-y-3 rounded-lg bg-gray-50 p-4">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{t('Device ID')}</dt>
            <dd className="mt-1 break-all font-mono text-sm text-gray-900">{newCredential?.id}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{t('Secret')}</dt>
            <dd className="mt-1 break-all font-mono text-sm text-gray-900">
              {newCredential?.device_secret}
            </dd>
          </div>
        </dl>
        <ModalFooter>
          <Button onClick={() => setNewCredential(null)}>{t('I have saved it')}</Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmModal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        onConfirm={handleConfirmDelete}
        title={t('Delete Device')}
        message={t('Are you sure you want to delete {{name}}? This action cannot be undone.', { name: selectedDevice?.name })}
        confirmText={t('Delete')}
        variant="danger"
        isLoading={isSubmitting}
      />

      <ConfirmModal
        isOpen={isRegenerateOpen}
        onClose={() => setIsRegenerateOpen(false)}
        onConfirm={handleConfirmRegenerate}
        title={t('Regenerate device secret')}
        message={t(
          'Regenerating the secret disconnects the current kiosk session. Continue for {{name}}?',
          { name: selectedDevice?.name }
        )}
        confirmText={t('Regenerate secret')}
        variant="danger"
        isLoading={regenerateMutation.isPending}
      />
    </>
  );
}

export default DevicesPage;
