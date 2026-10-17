import { useCallback, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeSidebar = useCallback(() => {
    setIsMobileSidebarOpen(false);
    requestAnimationFrame(() => menuButtonRef.current?.focus());
  }, []);

  return (
    <div className="min-h-screen bg-surface-muted text-foreground">
      <Sidebar isMobileOpen={isMobileSidebarOpen} onClose={closeSidebar} />
      <div className="lg:pl-64">
        <Header
          menuButtonRef={menuButtonRef}
          onOpenSidebar={() => setIsMobileSidebarOpen(true)}
        />
        <main id="main-content" className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
