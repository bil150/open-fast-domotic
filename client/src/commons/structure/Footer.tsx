import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-600 dark:bg-gray-800 text-white p-2 pb-4 hidden md:block flex-shrink-0">
      <div className="container mx-auto text-center">
        <p>open-fast-domotic 0.1.0.0 - @bil150 - &copy; {new Date().getFullYear()}</p>
        <p className="text-xs text-gray-400 mt-1">GPL-3.0 License</p>
      </div>
    </footer>
  );
};

export default Footer;