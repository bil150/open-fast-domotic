
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { VDeviceControl } from './commons/view/VDeviceControl';
import { V404 } from './commons/view/V404';
import Header from './commons/structure/Header';
import Footer from './commons/structure/Footer';
import './style/index.css';
import '@fontsource/orbitron';
import { useEffect, useState } from 'react';
import { VSettings } from './commons/view/VSettings';
import VAbout from './commons/view/VAbout';
import { VScenes } from './commons/view/VScenes';
import { VZones } from './commons/view/VZones';
import { VAutomations } from './commons/view/VAutomations';
   
function initAppConfig() {
  // Disable zoom
  const metaViewport = document.createElement('meta');
  metaViewport.name = 'viewport';
  metaViewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
  document.head.appendChild(metaViewport);

  // Disable scroll
  document.body.style.overflow = 'hidden';

  // Disable pull-to-refresh
  const disablePullToRefresh = (event: TouchEvent) => {
    if (event.touches.length > 1) {
      event.preventDefault();
    }
  };
  document.addEventListener('touchmove', disablePullToRefresh, { passive: false });

  // Cleanup function to remove the meta tag, restore scroll, and remove event listener
  return () => {
    document.head.removeChild(metaViewport);
    document.body.style.overflow = '';
    document.removeEventListener('touchmove', disablePullToRefresh);
  };
}

function App() {

  const [isNightMode, setIsNightMode] = useState<boolean>(() => localStorage.getItem('nightMode') === 'true');

  useEffect(() => {
    if (isNightMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('nightMode', JSON.stringify(isNightMode));
  }, [isNightMode]);


  const toggleNightMode = () => {
    setIsNightMode(!isNightMode);
  };

  useEffect(() => initAppConfig(), []);

  return (
    <BrowserRouter>
      <div className="flex flex-col font-orbitron h-dvh bg-gray-100 dark:bg-gray-900 dark:text-white w-full">
        <Header isNightMode={isNightMode} toggleNightMode={toggleNightMode} />
        <main className="flex-1 min-h-0 w-full flex justify-center items-center px-2 py-2 md:px-4 md:py-6">
          <Routes>
            <Route path="/" element={<VDeviceControl />} />
            <Route path="404" element={<V404 />} />
            <Route path="zones" element={<VZones/>}/>
            <Route path="scenes" element={<VScenes/>}/>
            <Route path="automations" element={<VAutomations/>}/>
            <Route path="settings" element={<VSettings/>}/>
            <Route path="about" element={<VAbout/>}/>
          </Routes>
        </main>
        <Footer />

      </div>
    </BrowserRouter>
  );
}

export default App;