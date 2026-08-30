import { useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';

function ModalHarness() {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)}>
        Open enrollment
      </button>
      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Enrollment"
        description="Capture a clear photo."
      >
        <button type="button">Capture</button>
      </Modal>
    </>
  );
}

describe('UI primitives', () => {
  it('associates labels and errors with inputs', () => {
    render(<Input label="Employee ID" error="Employee ID is required" />);

    const input = screen.getByLabelText('Employee ID');
    const error = screen.getByRole('alert');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', error.id);
  });

  it('opens on the dialog top layer, handles Escape, and restores focus', async () => {
    const user = userEvent.setup();
    render(<ModalHarness />);
    const trigger = screen.getByRole('button', { name: 'Open enrollment' });

    await user.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Enrollment' });
    expect(dialog).toHaveAttribute('open');
    expect(screen.getByText('Capture a clear photo.')).toHaveAttribute(
      'id',
      dialog.getAttribute('aria-describedby')
    );
    await waitFor(() => expect(screen.getByRole('button', { name: 'Close dialog' })).toHaveFocus());

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });
});
