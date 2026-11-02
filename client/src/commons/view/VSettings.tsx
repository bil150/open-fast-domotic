import { useTranslation } from 'react-i18next';

export function VSettings() {
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  return (
    <div className="page-card">
      <div className="flex flex-wrap justify-between items-center gap-2 px-4 md:px-6 py-2">
        <h2 className="text-2xl">{t('SETTINGS')}</h2>
      </div>

      <ul className="flex flex-col space-y-2 p-4 overflow-y-auto">
        <li className="flex items-center justify-between gap-4 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900">
          <label htmlFor="language" className="text-lg font-semibold">
            {t('CHANGE_LANGUAGE')}
          </label>
          <select
            id="language"
            onChange={(e) => changeLanguage(e.target.value)}
            value={i18n.language}
            className="bg-gray-200 dark:bg-gray-700 rounded p-2"
          >
            <option value="en">English</option>
            <option value="fr">Français</option>
            <option value="nl">Nederlands</option>
            <option value="ar">العربية</option>
          </select>
        </li>
      </ul>
    </div>
  );
}

export default VSettings;
