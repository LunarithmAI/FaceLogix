interface FaceGuideProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeStyles = {
  sm: 'w-32 h-44',
  md: 'w-48 h-64',
  lg: 'w-56 h-72',
};

export function FaceGuide({ size = 'md', className = '' }: FaceGuideProps) {
  return (
    <div className={`absolute inset-0 flex items-center justify-center pointer-events-none ${className}`}>
      <div
        className={`
          ${sizeStyles[size]}
          border-4 border-white/50 rounded-full
          relative
        `}
        style={{
          boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.4)',
        }}
      >
        {/* Corner indicators */}
        <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-8 h-1 bg-white/80 rounded-full" />
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-8 h-1 bg-white/80 rounded-full" />
        <div className="absolute top-1/2 -left-1 -translate-y-1/2 w-1 h-8 bg-white/80 rounded-full" />
        <div className="absolute top-1/2 -right-1 -translate-y-1/2 w-1 h-8 bg-white/80 rounded-full" />
      </div>
    </div>
  );
}

export default FaceGuide;
