import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { changeLanguage, translate as t } from '@/i18n';

describe('language switcher', () => {
  afterEach(async () => {
    await changeLanguage('en');
  });

  it('switches the interface to Vietnamese and persists the choice', async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    await user.selectOptions(screen.getByRole('combobox', { name: 'Language' }), 'vi');

    expect(await screen.findByRole('combobox', { name: 'Ngôn ngữ' })).toHaveValue('vi');
    expect(document.documentElement).toHaveAttribute('lang', 'vi');
    expect(window.localStorage.getItem('facelogix-language')).toBe('vi');
    expect(t('Check In')).toBe('Chấm vào');
  });
});
