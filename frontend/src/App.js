import React from 'react';

const target = 'https://profitenginev5.vercel.app';

export default function App() {
  React.useEffect(() => {
    window.location.href = target;
  }, []);

  return (
    <main style={{ fontFamily: 'system-ui', textAlign: 'center', padding: '4rem' }}>
      <h1>TokenForge</h1>
      <p>TokenForge has been consolidated into the active ProfitEngine v5 control layer.</p>
      <p>Redirecting now...</p>
      <a href={target}>Open ProfitEngine v5</a>
    </main>
  );
}
