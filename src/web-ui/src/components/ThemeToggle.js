import React from 'react';
import { useTheme } from '../hooks/useTheme';
import '../styles/ThemeToggle.css';

function ThemeToggle() {
  const { darkMode, toggleTheme } = useTheme();

  return (
    <div className="theme-toggle">
      <span className="theme-toggle-icon">☀️</span>
      <label className="theme-toggle-switch">
        <input 
          type="checkbox" 
          checked={darkMode} 
          onChange={toggleTheme}
          aria-label="Toggle dark mode"
        />
        <span className="theme-toggle-slider"></span>
      </label>
      <span className="theme-toggle-icon">🌙</span>
    </div>
  );
}

export default ThemeToggle;
