import { GlobeAltIcon } from '@heroicons/react/24/outline';
import { useTranslation } from 'react-i18next';
import { changeLanguage, getCurrentLanguage, translate as t, type SupportedLanguage } from '@/i18n';

interface LanguageSwitcherProps {
  compact?: boolean;
  inverted?: boolean;
}

export function LanguageSwitcher({ compact = false, inverted = false }: LanguageSwitcherProps) {
  useTranslation();
  const language = getCurrentLanguage();
  const textColor = inverted ? 'text-white' : 'text-gray-700';
  const borderColor = inverted ? 'border-white/40' : 'border-gray-300';
  const backgroundColor = inverted ? 'bg-white/10' : 'bg-white';

  return (
    <div className={compact ? 'relative flex items-center' : 'space-y-1'}>
      {!compact && (
        <label htmlFor="application-language" className={`block text-sm font-medium ${textColor}`}>
          {t('Language')}
        </label>
      )}
      <div className="relative">
        <GlobeAltIcon
          className={`pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 ${inverted ? 'text-white/80' : 'text-gray-500'}`}
          aria-hidden="true"
        />
        <select
          id={compact ? undefined : 'application-language'}
          aria-label={compact ? t('Language') : undefined}
          value={language}
          onChange={(event) => void changeLanguage(event.target.value as SupportedLanguage)}
          className={`min-h-11 appearance-none rounded-lg border py-2 pl-10 pr-8 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 ${borderColor} ${backgroundColor} ${textColor}`}
        >
          <option className="text-gray-900" value="en">{compact ? 'EN' : t('English')}</option>
          <option className="text-gray-900" value="vi">{compact ? 'VI' : t('Vietnamese')}</option>
        </select>
      </div>
    </div>
  );
}

export default LanguageSwitcher;
