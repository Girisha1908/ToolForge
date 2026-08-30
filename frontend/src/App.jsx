import React, { useState } from 'react';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [resetKey, setResetKey] = useState(0);

  const handleResetApp = () => {
    setActiveTab('dashboard');
    setResetKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface font-sans flex flex-col">
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onReset={handleResetApp}
      />
      <div className="flex-1">
        <Dashboard key={resetKey} activeTab={activeTab} />
      </div>
    </div>
  );
}

export default App;
