
import { Link } from "react-router-dom";
import React, { useState } from "react";

import { useTranslation } from 'react-i18next';
interface HeaderProps { 
  isNightMode: boolean; 
  toggleNightMode: () => void;
}

const Header: React.FC<HeaderProps> = ({ isNightMode, toggleNightMode }) => {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };
 


  function renderToggleNightMode() {
    return (
      <label
        htmlFor="night-mode-toggle"
        className="flex items-center cursor-pointer"
      >
        <div className="relative">
          <input
            id="night-mode-toggle"
            type="checkbox"
            className="sr-only"
            checked={isNightMode}
            onChange={toggleNightMode}
          />
          <div className="block bg-gray-400 dark:bg-gray-600 w-14 h-8 rounded-full"></div>
          <div
            className={`text-white dot absolute left-1 top-1 bg-gray-300 dark:bg-gray-400 w-6 h-6 rounded-full transition ${
              isNightMode ? "transform translate-x-full " : ""
            }`}
          >
            {isNightMode ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-6 h-6 "
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-6 h-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z"
                />
              </svg>
            )}
          </div>
        </div>
      </label>
    );
  }

  return (
    <header className="bg-gray-500 text-white p-4 dark:bg-gray-800 dark:text-gray-200 ">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex space-x-3 items-center ">
          <Link to="/" className="flex items-center">
            <h1 className="text-xl font-bold" aria-label="open-fast-domotic">
              <span className="md:hidden">OFD</span>
              <span className="hidden md:inline">open-fast-domotic</span>
            </h1>
          </Link>
        </div>

        <div className="flex items-center space-x-4">
          <div className="md:hidden relative">
            <button onClick={toggleMenu} className="focus:outline-none ">
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d={isOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16m-7 6h7"}
                ></path>
              </svg>
            </button>
            {isOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white text-black rounded-lg shadow-lg z-10 dark:bg-gray-700 dark:text-gray-200">
                <ul className="flex flex-col space-y-2 p-2">
                  <li>
                    <Link
                      to="/"
                      className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {t('HOME')}
                    </Link>
                  </li>
                  <li>
                    <Link
                      to="/zones"
                      className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {t('ZONES')}
                    </Link>
                  </li>
                  <li>
                    <Link
                      to="/scenes"
                      className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {t('SCENES')}
                    </Link>
                  </li>
                  <li>
                    <Link
                      to="/automations"
                      className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {t('AUTOMATIONS')}
                    </Link>
                  </li>
                  <li>
                    <Link
                      to="/about"
                      className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {t('ABOUT')}
                    </Link>
                  </li>
                  <li>
                    <Link
                      to="/settings"
                      className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {t('SETTINGS')}
                    </Link>
                  </li>
                  <li>
                    <div className="block px-4 py-2 hover:bg-gray-200 dark:hover:bg-gray-600">
                      {renderToggleNightMode()}
                    </div>
                  </li>
                </ul>
              </div>
            )}
          </div>
        </div>
        <nav className="hidden md:flex md:items-center md:space-x-4">
          <ul className="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-4">
            <li>
              <Link to="/" className="hover:underline">
                {t('HOME')}
              </Link>
            </li>
            <li>
              <Link to="/zones" className="hover:underline">
                {t('ZONES')}
              </Link>
            </li>
            <li>
              <Link to="/scenes" className="hover:underline">
                {t('SCENES')}
              </Link>
            </li>
            <li>
              <Link to="/automations" className="hover:underline">
                {t('AUTOMATIONS')}
              </Link>
            </li>
            <li>
              <Link to="/about" className="hover:underline">
                {t('ABOUT')}
              </Link>
            </li>
            <li>
              <Link to="/settings" className="hover:underline">
                {t('SETTINGS')}
              </Link>
            </li>
            <li>
              <div className="flex items-center space-x-2">
                {renderToggleNightMode()}
              </div>
            </li>

          </ul>
        </nav>
      </div>
    </header>
  );
};

export default Header;