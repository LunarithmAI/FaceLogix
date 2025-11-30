import { useState } from 'react';
import {
  PencilIcon,
  TrashIcon,
  EllipsisVerticalIcon,
  SignalIcon,
  SignalSlashIcon,
} from '@heroicons/react/24/outline';
import type { Device } from '@/types/device';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { formatSmartDate } from '@/utils/date';

interface DeviceTableProps {
  devices: Device[];
  isLoading?: boolean;
  onEdit?: (device: Device) => void;
  onDelete?: (device: Device) => void;
  onToggleStatus?: (device: Device) => void;
}

export function DeviceTable({
  devices,
  isLoading = false,
  onEdit,
  onDelete,
  onToggleStatus,
}: DeviceTableProps) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const getDeviceTypeIcon = (type: string) => {
    switch (type) {
      case 'kiosk':
        return 'Kiosk';
      case 'mobile':
        return 'Mobile';
      case 'web':
        return 'Web';
      default:
        return type;
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No devices found</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Device
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Location
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Last Active
            </th>
            <th className="relative px-6 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {devices.map((device) => (
            <tr key={device.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div
                    className={`w-10 h-10 flex-shrink-0 rounded-lg flex items-center justify-center ${
                      device.status === 'active' ? 'bg-green-100' : 'bg-gray-100'
                    }`}
                  >
                    {device.status === 'active' ? (
                      <SignalIcon className="w-5 h-5 text-green-600" />
                    ) : (
                      <SignalSlashIcon className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900">
                      {device.name}
                    </div>
                    <div className="text-xs text-gray-500 font-mono">
                      {device.id.slice(0, 8)}...
                    </div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Badge variant="default">{getDeviceTypeIcon(device.type)}</Badge>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={device.status} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {device.location || '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {device.last_active_at
                  ? formatSmartDate(device.last_active_at)
                  : 'Never'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div className="relative">
                  <button
                    onClick={() =>
                      setOpenMenuId(openMenuId === device.id ? null : device.id)
                    }
                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    <EllipsisVerticalIcon className="w-5 h-5" />
                  </button>

                  {openMenuId === device.id && (
                    <>
                      <div
                        className="fixed inset-0 z-10"
                        onClick={() => setOpenMenuId(null)}
                      />
                      <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                        <button
                          onClick={() => {
                            onEdit?.(device);
                            setOpenMenuId(null);
                          }}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        >
                          <PencilIcon className="w-4 h-4 mr-3" />
                          Edit
                        </button>
                        <button
                          onClick={() => {
                            onToggleStatus?.(device);
                            setOpenMenuId(null);
                          }}
                          className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        >
                          {device.status === 'active' ? (
                            <>
                              <SignalSlashIcon className="w-4 h-4 mr-3" />
                              Deactivate
                            </>
                          ) : (
                            <>
                              <SignalIcon className="w-4 h-4 mr-3" />
                              Activate
                            </>
                          )}
                        </button>
                        <div className="border-t border-gray-100 my-1" />
                        <button
                          onClick={() => {
                            onDelete?.(device);
                            setOpenMenuId(null);
                          }}
                          className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                        >
                          <TrashIcon className="w-4 h-4 mr-3" />
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DeviceTable;
