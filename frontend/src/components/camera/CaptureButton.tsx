import { CameraIcon } from '@heroicons/react/24/solid';

interface CaptureButtonProps {
  onClick: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  size?: 'md' | 'lg' | 'xl';
  className?: string;
}

const sizeStyles = {
  md: 'w-16 h-16',
  lg: 'w-20 h-20',
  xl: 'w-24 h-24',
};

const iconSizeStyles = {
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-10 h-10',
};

export function CaptureButton({
  onClick,
  isLoading = false,
  disabled = false,
  size = 'lg',
  className = '',
}: CaptureButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`
        ${sizeStyles[size]}
        rounded-full bg-white shadow-lg
        flex items-center justify-center
        transition-all duration-200
        hover:scale-105 hover:shadow-xl
        active:scale-95
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
        focus:outline-none focus:ring-4 focus:ring-primary-500/50
        ${className}
      `}
      aria-label="Capture photo"
    >
      {isLoading ? (
        <svg
          className={`animate-spin text-primary-600 ${iconSizeStyles[size]}`}
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        <div className="relative">
          {/* Outer ring */}
          <div className={`absolute inset-0 rounded-full border-4 border-primary-600 ${sizeStyles[size]}`} />
          {/* Inner circle */}
          <div
            className={`
              ${size === 'md' ? 'w-12 h-12' : size === 'lg' ? 'w-14 h-14' : 'w-16 h-16'}
              rounded-full bg-primary-600 flex items-center justify-center
              m-1
            `}
          >
            <CameraIcon className={`text-white ${iconSizeStyles[size]}`} />
          </div>
        </div>
      )}
    </button>
  );
}

export default CaptureButton;
