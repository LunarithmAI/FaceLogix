import { forwardRef, useId } from 'react';
import type { SelectHTMLAttributes } from 'react';
import { ChevronDownIcon } from '@heroicons/react/20/solid';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      error,
      helperText,
      className = '',
      id,
      children,
      'aria-describedby': ariaDescribedBy,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const selectId = id ?? generatedId;
    const errorId = `${selectId}-error`;
    const helperId = `${selectId}-helper`;
    const describedBy =
      [ariaDescribedBy, error ? errorId : undefined, !error && helperText ? helperId : undefined]
        .filter((value) => value !== undefined)
        .join(' ') || undefined;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={selectId} className="mb-1 block text-sm font-medium text-gray-700">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            aria-invalid={error !== undefined}
            aria-describedby={describedBy}
            className={`
              block min-h-11 w-full appearance-none rounded-lg border bg-surface py-2 pl-4 pr-10
              transition-colors duration-200 motion-reduce:transition-none
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0
              ${error
                ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-primary-500 focus:ring-primary-500'
              }
              disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500
              ${className}
            `}
            {...props}
          >
            {children}
          </select>
          <ChevronDownIcon
            className="pointer-events-none absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
        </div>
        {error && (
          <p id={errorId} className="mt-1 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={helperId} className="mt-1 text-sm text-gray-500">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
