import { useState, useEffect, useCallback } from 'react';
import { PlusIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal, ConfirmModal, ModalFooter } from '@/components/ui/Modal';
import { DeviceTable } from '@/components/admin/DeviceTable';
import { Loading } from '@/components/ui/Loading';
import { devicesApi, type DeviceListResponse } from '@/services/devices';
import type { Device, DeviceRegistration, DeviceType } from '@/types/device';

export function DevicesPage() {
  const [devices, setDevices] = useState<DeviceListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    type: 'kiosk' as DeviceType,
    location: '',
  });

  const loadDevices = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await devicesApi.list({ page, search, limit: 10 });
      setDevices(data);
    } catch (error) {
      console.error('Failed to load devices:', error);
    } finally {
      setIsLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleCreate = () => {
    setSelectedDevice(null);
    setFormData({ name: '', type: 'kiosk', location: '' });
    setIsFormOpen(true);
  };

  const handleEdit = (device: Device) => {
    setSelectedDevice(device);
    setFormData({
      name: device.name,
      type: device.type,
      location: device.location || '',
    });
    setIsFormOpen(true);
  };

  const handleDelete = (device: Device) => {
    setSelectedDevice(device);
    setIsDeleteOpen(true);
  };

  const handleToggleStatus = async (device: Device) => {
    try {
      if (device.status === 'active') {
        await devicesApi.deactivate(device.id);
      } else {
        await devicesApi.activate(device.id);
      }
      loadDevices();
    } catch (error) {
      console.error('Failed to toggle device status:', error);
    }
  };

  const handleFormSubmit = async () => {
    setIsSubmitting(true);
    try {
      const data: DeviceRegistration = {
        name: formData.name,
        type: formData.type,
        location: formData.location || undefined,
      };

      if (selectedDevice) {
        await devicesApi.update(selectedDevice.id, data);
      } else {
        await devicesApi.register(data);
      }
      setIsFormOpen(false);
      loadDevices();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!selectedDevice) return;
    setIsSubmitting(true);
    try {
      await devicesApi.delete(selectedDevice.id);
      setIsDeleteOpen(false);
      loadDevices();
    } finally {
      setIsSubmitting(false);
    }
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
          {isLoading ? (
            <div className="py-12">
              <Loading size="lg" text="Loading devices..." />
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
          <Input
            label="Device Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Main Entrance Kiosk"
            required
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Device Type
            </label>
            <select
              value={formData.type}
              onChange={(e) =>
                setFormData({ ...formData, type: e.target.value as DeviceType })
              }
              className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="kiosk">Kiosk</option>
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
