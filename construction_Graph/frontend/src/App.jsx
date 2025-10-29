import { useState, useEffect } from 'react';
import DocumentUpload from './components/DocumentUpload';
import QueryPanel from './components/QueryPanel';
import GraphVisualization from './components/GraphVisualization';
import MetricsDisplay from './components/MetricsDisplay';
import AnswerDisplay from './components/AnswerDisplay';
import { api } from './services/api';

export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [backendError, setBackendError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkBackend();
    // Refresh metrics every 5 seconds
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      await api.health();
      setBackendError(null);
      setLoading(false);
      fetchMetrics();
    } catch (error) {
      setBackendError('Backend not available. Make sure it\'s running on http://localhost:8000');
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const data = await api.getMetrics();
      setMetrics(data);
      setBackendError(null);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  const handleQueryResult = (data) => {
    setAnswer(data);

    // Handle graph data if present
    if (data.nodes && data.nodes.length > 0) {
      const nodes = data.nodes.map(n => ({
        id: n.id,
        name: n.properties?.name || n.id,
        type: n.label
      }));

      const links = data.edges?.map(e => ({
        source: e.source,
        target: e.target,
        type: e.type
      })) || [];

      setGraphData({ nodes, links });
    }
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        color: '#e2e8f0'
      }}>
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>🏗️ Construction GraphRAG</h1>
          <div style={{
            width: '50px',
            height: '50px',
            border: '4px solid #334155',
            borderTop: '4px solid #667eea',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto'
          }} />
          <p style={{ marginTop: '1rem', opacity: 0.7 }}>Connecting to backend...</p>
        </div>
      </div>
    );
  }

  if (backendError) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        color: '#ef4444',
        padding: '2rem'
      }}>
        <div style={{
          textAlign: 'center',
          background: '#1e293b',
          padding: '3rem',
          borderRadius: '1rem',
          border: '2px solid #ef4444'
        }}>
          <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️ Backend Connection Error</h1>
          <p style={{ marginBottom: '2rem' }}>{backendError}</p>
          <button
            onClick={checkBackend}
            style={{
              padding: '0.75rem 1.5rem',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: 'bold'
            }}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0' }}>
      <header style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '2rem',
        boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
      }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          🏗️ Construction GraphRAG
        </h1>
        <p style={{ opacity: 0.9 }}>
          Intelligent document analysis for construction projects
        </p>
      </header>

      <MetricsDisplay metrics={metrics} />

      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: '2rem',
        display: 'grid',
        gridTemplateColumns: '1fr',  /* Changed from '1fr 1fr' to single column */
        gap: '2rem'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <DocumentUpload onUploadSuccess={fetchMetrics} />
          <QueryPanel onQueryResult={handleQueryResult} />
          <AnswerDisplay answer={answer} />
        </div>

        {/* HIDDEN FOR DEMO: Knowledge Graph */}
        {/* <GraphVisualization graphData={graphData} /> */}
      </div>
    </div>
  );
}
