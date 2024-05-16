import React, { useState } from 'react';

const AlertBox = ({ title, body }) => {
  const [isVisible, setIsVisible] = useState(true);

  const closeAlert = () => {
    setIsVisible(false);
  };

  const containerClasses = "fixed inset-0 flex items-center justify-center z-50";
  const alertBoxClasses = "bg-white dark:bg-zinc-800 p-6 rounded-lg shadow-lg max-w-sm";
  const messageClasses = "text-zinc-800 dark:text-zinc-200 text-lg font-medium mb-4";
  const buttonClasses = "bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded";

  if (!isVisible && (!title || !body)) return null;

  return (
    <div className={containerClasses}>
      <div className={alertBoxClasses}>
        <p className={messageClasses}>
          {title}: {body}
        </p>
        <button onClick={closeAlert} className={buttonClasses}>
          Ok
        </button>
      </div>
    </div>
  );
};

export default AlertBox;