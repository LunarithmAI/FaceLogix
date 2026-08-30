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
import type { Device, DeviceCredential, DeviceRegistration, DeviceType } from '@/types/device';
import { queryClient, queryKeys } from '@/lib/queryClient';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';

export function DevicesPage() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search);
  const [page, setPage] = useState(1);

  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [newCredential, setNewCredential] = useState<DeviceCredential | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    device_type: 'kiosk' as DeviceType,
    location: '',
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
        const device = await devicesApi.update(input.deviceId, input.data);
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
  const devices = devicesQuery.data;
  const isSubmitting = saveMutation.isPending || deleteMutation.isPending;
  const actionError = saveMutation.error ?? deleteMutation.error ?? toggleMutation.error;

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleCreate = () => {
    setSelectedDevice(null);
    setFormData({ name: '', device_type: 'kiosk', location: '' });
    setIsFormOpen(true);
  };

  const handleEdit = (device: Device) => {
    setSelectedDevice(device);
    setFormData({
      name: device.name,
      device_type: device.device_type,
      location: device.location || '',
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

  const handleFormSubmit = () => {
    const data: DeviceRegistration = {
      name: formData.name,
      device_type: formData.device_type,
      location: formData.location || undefined,
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

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Devices</h1>
            <p className="text-gray-500 mt-1">Manage check-in devices and kiosks</p>
          </div>
          <Button leftIcon={<PlusIcon className="w-5 h-5" />} onClick={handleCreate}>
            Add Device
          </Button>
        </div>

        {actionError !== null && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" role="alert">
            {actionError.message}
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
                  placeholder="Search devices..."
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
              <Loading size="lg" text="Loading devices..." />
            </div>
          ) : devicesQuery.error !== null ? (
            <div className="p-6 text-center text-red-700" role="alert">
              <p>{devicesQuery.error.message}</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => void devicesQuery.refetch()}
              >
                Try again
              </Button>
            </div>
          ) : (
            <>
              <DeviceTable
                devices={devices?.items || []}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onToggleStatus={handleToggleStatus}
              />

              {/* Pagination */}
              {devices && devices.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    Page {devices.page} of {devices.pages} ({devices.total} devices)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === devices.pages}
                    >
                      Next
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
        title={selectedDevice ? 'Edit Device' : 'Register Device'}
      >
        <div className="space-y-4">
          {saveMutation.error !== null && (
            <p className="text-sm text-red-700" role="alert">
              {saveMutation.error.message}
            </p>
          )}
          <Input
            label="Device Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Main Entrance Kiosk"
            required
          />

          <div>
            <label htmlFor="device-type" className="block text-sm font-medium text-gray-700 mb-1">
              Device Type
            </label>
            <select
              id="device-type"
              value={formData.device_type}
              onChange={(e) =>
                setFormData({ ...formData, device_type: e.target.value as DeviceType })
              }
              className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="kiosk">Kiosk</option>
              <option value="tablet">Tablet</option>
              <option value="mobile">Mobile</option>
              <option value="web">Web</option>
            </select>
          </div>

          <Input
            label="Location"
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            placeholder="Building A, Floor 1"
          />
        </div>

        <ModalFooter>
          <Button variant="secondary" onClick={() => setIsFormOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleFormSubmit} isLoading={isSubmitting}>
            {selectedDevice ? 'Update' : 'Register'}
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        isOpen={newCredential !== null}
        onClose={() => setNewCredential(null)}
        title="Save device credentials"
      >
        <p className="text-sm text-gray-600">
          This secret is shown once. Store it in the device configuration before closing.
        </p>
        <dl className="mt-4 space-y-3 rounded-lg bg-gray-50 p-4">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Device ID</dt>
            <dd className="mt-1 break-all font-mono text-sm text-gray-900">{newCredential?.id}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Secret</dt>
            <dd className="mt-1 break-all font-mono text-sm text-gray-900">
              {newCredential?.device_secret}
            </dd>
          </div>
        </dl>
        <ModalFooter>
          <Button onClick={() => setNewCredential(null)}>I have saved it</Button>
        </ModalFooter>
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmModal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Device"
        message={`Are you sure you want to delete ${selectedDevice?.name}? This action cannot be undone.`}
        confirmText="Delete"
        variant="danger"
        isLoading={isSubmitting}
      />
    </>
  );
}

export default DevicesPage;
