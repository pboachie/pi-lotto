import React, { useEffect } from 'react';

function PiLotto() {
  useEffect(() => {
    const Pi = window.Pi;
    Pi.init({ version: "2.0" });
  }, []);

  return (
    <div>
      <h2>Pi-Lotto</h2>
      {/* Add your lotto component content here */}
    </div>
  );
}

export default PiLotto;