// frontend/src/components/LoadingSpinner.js
import React from 'react';

const LoadingSpinner = () => {
  return (
    <div className="loading-overlay">
      <div className="spinner-container">
        <div className="spinner"></div>
        <div className="loading-text">
          <h3>Processing...</h3>
          <p>AI algorithms are working hard to find the best matches</p>
        </div>
      </div>
    </div>
  );
};

export default LoadingSpinner;
