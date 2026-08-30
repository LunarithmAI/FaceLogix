import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface DisclosureMenuProps {
  label: string;
  trigger: ReactNode;
  children: (close: () => void) => ReactNode;

  width?: number;
  align?: 'left' | 'right';
  triggerClassName?: string;
}
export const disclosureMenuItemClass =
  'flex min-h-11 w-full items-center px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:bg-gray-50';

export function DisclosureMenu({
  label,
  trigger,
  children,
  width = 192,
  align = 'right',
  triggerClassName = '',
}: DisclosureMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ left: 8, top: 8 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const close = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const open = () => {
    const triggerRect = triggerRef.current?.getBoundingClientRect();
    if (triggerRect !== undefined) {
      const preferredLeft = align === 'right' ? triggerRect.right - width : triggerRect.left;
      setPosition({
        left: Math.max(8, Math.min(preferredLeft, window.innerWidth - width - 8)),
        top: Math.min(triggerRect.bottom + 8, window.innerHeight - 8),
      });
    }
    setIsOpen(true);
  };

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const menu = menuRef.current;
    const triggerRect = triggerRef.current?.getBoundingClientRect();
    const menuRect = menu?.getBoundingClientRect();
    if (
      triggerRect !== undefined &&
      menuRect !== undefined &&
      menuRect.bottom > window.innerHeight - 8
    ) {
      setPosition((current) => ({
        ...current,
        top: Math.max(8, triggerRect.top - menuRect.height - 8),
      }));
    }
    const items = menu?.querySelectorAll<HTMLButtonElement>('button:not([disabled])');
    items?.[0]?.focus();

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!menuRef.current?.contains(target) && !triggerRef.current?.contains(target)) {
        setIsOpen(false);
      }
    };
    const handleViewportChange = () => setIsOpen(false);
    document.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('scroll', handleViewportChange, true);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('resize', handleViewportChange);
      window.removeEventListener('scroll', handleViewportChange, true);
    };
  }, [isOpen]);

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not([disabled])')
    );
    if (items.length === 0) {
      return;
    }
    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      items[(currentIndex + 1) % items.length]?.focus();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      items[(currentIndex - 1 + items.length) % items.length]?.focus();
    } else if (event.key === 'Home') {
      event.preventDefault();
      items[0]?.focus();
    } else if (event.key === 'End') {
      event.preventDefault();
      items[items.length - 1]?.focus();
    }
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={isOpen ? menuId : undefined}
        className={`min-h-11 min-w-11 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 ${triggerClassName}`}
        onClick={() => (isOpen ? close() : open())}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            open();
          }
        }}
      >
        {trigger}
      </button>
      {isOpen &&
        createPortal(
          <div
            ref={menuRef}
            id={menuId}
            role="menu"
            className="fixed z-[70] overflow-hidden rounded-lg border border-gray-200 bg-white py-1 shadow-xl"
            style={{ left: position.left, top: position.top, width }}
            onKeyDown={handleMenuKeyDown}
          >
            {children(close)}
          </div>,
          document.body
        )}
    </>
  );
}

export default DisclosureMenu;
