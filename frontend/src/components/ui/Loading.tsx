interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'gray';
  className?: string;
  text?: string;
}

const sizeStyles = {
  sm: 'h-4 w-4',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
};

const colorStyles = {
  primary: 'text-primary-600',
  gray: 'text-gray-400',
};

export function Loading({
  size = 'md',
  color = 'primary',
  className = '',
  text,
}: LoadingProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 ${className}`}
      role="status"
      aria-live="polite"
      aria-label={text ?? 'Loading'}
    >
      <svg
        className={`animate-spin motion-reduce:animate-none ${sizeStyles[size]} ${colorStyles[color]}`}
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
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
      {text !== undefined && <p className={`text-sm ${colorStyles[color]}`}>{text}</p>}
    </div>
  );
}

export default Loading;
