import { useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Alert } from '@/components/ui/Alert';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Pagination } from '@/components/ui/Pagination';
import { Select } from '@/components/ui/Select';

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

  it('associates labels and errors with selects', () => {
    render(
      <Select label="Unit" error="Unit is required">
        <option value="">Select unit</option>
      </Select>
    );

    const select = screen.getByRole('combobox', { name: 'Unit' });
    expect(select).toHaveAttribute('aria-invalid', 'true');
    expect(select).toHaveAttribute('aria-describedby', screen.getByRole('alert').id);
  });

  it('announces errors assertively and other alerts politely', () => {
    const { rerender } = render(<Alert>Export failed</Alert>);
    expect(screen.getByRole('alert')).toHaveTextContent('Export failed');

    rerender(<Alert variant="success">Saved</Alert>);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Saved');
  });

  it('pages within bounds and hides itself for a single page', async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    const { rerender } = render(
      <Pagination page={1} pages={3} total={25} itemLabel="users" onPageChange={onPageChange} />
    );

    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(onPageChange).toHaveBeenCalledWith(2);

    rerender(
      <Pagination page={1} pages={1} total={5} itemLabel="users" onPageChange={onPageChange} />
    );
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});
