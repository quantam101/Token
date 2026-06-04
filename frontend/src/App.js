import React from 'react';

export default function App() {
  React.useEffect(() => {
    window.location.href = 'https://profitengine-tau.vercel.app';
  }, []);
  return (
    <div style={{fontFamily:'system-ui',textAlign:'center',padding:'4rem'}}>
      <h2>TokenForge</h2>
      <p>This product has been integrated into ProfitEngine.</p>
      <p>Redirecting you now...</p>
      <a href='https://profitengine-tau.vercel.app'>Click here if not redirected</a>
    </div>
  );
}
