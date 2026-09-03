import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { PlusIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal, ConfirmModal, ModalFooter } from '@/components/ui/Modal';
import { DeviceTable } from '@/components/admin/DeviceTable';
import { Loading } from '@/components/ui/Loading';
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
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t('Devices')}</h1>
            <p className="text-gray-500 mt-1">{t('Manage check-in devices and kiosks')}</p>
          </div>
          <Button leftIcon={<PlusIcon className="w-5 h-5" />} onClick={handleCreate}>
            {t('Add Device')}
          </Button>
        </div>

        {actionError !== null && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" role="alert">
            {t(actionError.message)}
          </div>
        )}

        {/* Search */}
        <Card padding="sm">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <Input
                  type="search"
                  placeholder={t('Search devices...')}
                  value={search}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Devices Table */}
        <Card>
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

              {/* Pagination */}
              {devices && devices.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    {t('Page')} {devices.page} {t('of')} {devices.pages} ({devices.total} {t('devices')})
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      {t('Previous')}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === devices.pages}
                    >
                      {t('Next')}
                    </Button>
                  </div>
                </div>
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
          {saveMutation.error !== null && (
            <p className="text-sm text-red-700" role="alert">
              {t(saveMutation.error.message)}
            </p>
          )}
          <Input
            label={t('Device Name')}
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder={t('Main Entrance Kiosk')}
            required
          />

          <div>
            <label htmlFor="device-type" className="block text-sm font-medium text-gray-700 mb-1">
              {t('Device Type')}
            </label>
            <select
              id="device-type"
              value={formData.device_type}
              onChange={(e) =>
                setFormData({ ...formData, device_type: e.target.value as DeviceType })
              }
              className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="kiosk">{t('Kiosk')}</option>
              <option value="tablet">{t('Tablet')}</option>
              <option value="mobile">{t('Mobile')}</option>
              <option value="web">{t('Web')}</option>
            </select>
          </div>

          <Input
            label={t('Location')}
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            placeholder={t('Building A, Floor 1')}
          />

          <fieldset className="space-y-3 border border-gray-200 p-4">
            <legend className="px-1 text-sm font-semibold text-gray-900">
              {t('Kiosk actions')}
            </legend>
            <label className="flex min-h-11 items-center gap-3 text-sm text-gray-800">
              <input
                type="checkbox"
                checked={formData.settings.allow_check_in}
                onChange={(event) => setActionEnabled('allow_check_in', event.target.checked)}
                className="h-5 w-5 border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              {t('Allow check-in')}
            </label>
            <label className="flex min-h-11 items-center gap-3 text-sm text-gray-800">
              <input
                type="checkbox"
                checked={formData.settings.allow_check_out}
                onChange={(event) => setActionEnabled('allow_check_out', event.target.checked)}
                className="h-5 w-5 border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              {t('Allow check-out')}
            </label>
            {!formData.settings.allow_check_in && !formData.settings.allow_check_out && (
              <p className="text-sm text-amber-700" role="status">
                {t('This kiosk will be blocked until an action is enabled.')}
              </p>
            )}
          </fieldset>

          <div>
            <label
              htmlFor="default-mode"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              {t('Default mode')}
            </label>
            <select
              id="default-mode"
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
              className="block min-h-11 w-full border border-gray-300 bg-white px-4 py-2 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="check_in">{t('Check In')}</option>
              <option value="check_out">{t('Check Out')}</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="camera-facing"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              {t('Camera facing')}
            </label>
            <select
              id="camera-facing"
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
              className="block min-h-11 w-full border border-gray-300 bg-white px-4 py-2 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="user">{t('Front camera')}</option>
              <option value="environment">{t('Rear camera')}</option>
            </select>
          </div>

          {settingsError !== null && (
            <p className="text-sm text-red-700" role="alert">
              {settingsError}
            </p>
          )}
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
