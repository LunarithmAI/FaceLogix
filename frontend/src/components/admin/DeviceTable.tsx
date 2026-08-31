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
import {
  DisclosureMenu,
  disclosureMenuItemClass,
} from '@/components/ui/DisclosureMenu';
import { translate as t } from '@/i18n';

const DEVICE_TYPE_LABELS = {
  kiosk: 'Kiosk',
  tablet: 'Tablet',
  mobile: 'Mobile',
  web: 'Web',
} as const;

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


  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>{t('No devices found')}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500" role="region" aria-label={t('Devices table')} tabIndex={0}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Device')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Type')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Status')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Location')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Last Active')}
            </th>
            <th className="relative px-6 py-3">
              <span className="sr-only">{t('Actions')}</span>
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
                      device.is_active ? 'bg-green-100' : 'bg-gray-100'
                    }`}
                  >
                    {device.is_active ? (
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
                <Badge variant="default">{t(DEVICE_TYPE_LABELS[device.device_type])}</Badge>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={device.is_active ? 'active' : 'inactive'} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {device.location || '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {device.last_seen_at
                  ? formatSmartDate(device.last_seen_at)
                  : t('Never')}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <DisclosureMenu
                  label={t('Actions for {{name}}', { name: device.name })}
                  trigger={
                    <EllipsisVerticalIcon
                      className="mx-auto h-5 w-5 text-gray-500"
                      aria-hidden="true"
                    />
                  }
                >
                  {(close) => (
                    <>
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          close();
                          onEdit?.(device);
                        }}
                        className={disclosureMenuItemClass}
                      >
                        <PencilIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                        {t('Edit')}
                      </button>
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          close();
                          onToggleStatus?.(device);
                        }}
                        className={disclosureMenuItemClass}
                      >
                        {device.is_active ? (
                          <>
                            <SignalSlashIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                            {t('Deactivate')}
                          </>
                        ) : (
                          <>
                            <SignalIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                            {t('Activate')}
                          </>
                        )}
                      </button>
                      <div className="my-1 border-t border-gray-100" />
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          close();
                          onDelete?.(device);
                        }}
                        className={`${disclosureMenuItemClass} text-red-600 hover:bg-red-50 focus-visible:bg-red-50`}
                      >
                        <TrashIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                        {t('Delete')}
                      </button>
                    </>
                  )}
                </DisclosureMenu>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DeviceTable;
