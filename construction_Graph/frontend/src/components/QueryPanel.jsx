import { useState } from 'react';

export default function QueryPanel({ onQueryResult }) {
  const [question, setQuestion] = useState('');
  const [querying, setQuerying] = useState(false);

  const sampleQuestions = [
    "What references sheet A-201?",
    "Find components in Zone A",
    "Where is AHU-3 located?",
    "Show all electrical panels"
  ];

  const handleQuery = async () => {
    if (!question.trim()) return;

    setQuerying(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          max_results: 10
        })
      });

      const data = await response.json();
      
      if (onQueryResult) {
        onQueryResult(data);
      }
    } catch (error) {
      if (onQueryResult) {
        onQueryResult({
          answer: `Query failed: ${error.message}`,
          query_type: 'error',
          execution_time_ms: 0,
          sources: []
        });
      }
    } finally {
      setQuerying(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleQuery();
    }
  };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '0.75rem',
      padding: '1.5rem',
      boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
    }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        🔍 Query Knowledge Graph
      </h2>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
        {sampleQuestions.map((q, i) => (
          <button
            key={i}
            onClick={() => setQuestion(q)}
            style={{
              padding: '0.5rem 1rem',
              background: '#334155',
              color: '#e2e8f0',
              border: 'none',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.background = '#475569'}
            onMouseLeave={(e) => e.target.style.background = '#334155'}
          >
            {q}
          </button>
        ))}
      </div>

      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder="Ask a question about your construction documents... (Ctrl+Enter to search)"
        style={{
          width: '100%',
          minHeight: '100px',
          padding: '0.75rem',
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '0.5rem',
          color: '#e2e8f0',
          fontSize: '1rem',
          resize: 'vertical',
          fontFamily: 'inherit'
        }}
      />

      <button
        onClick={handleQuery}
        disabled={!question.trim() || querying}
        style={{
          marginTop: '1rem',
          width: '100%',
          padding: '0.75rem',
          background: querying ? '#475569' : '#8b5cf6',
          color: 'white',
          border: 'none',
          borderRadius: '0.5rem',
          fontWeight: 'bold',
          cursor: querying || !question.trim() ? 'not-allowed' : 'pointer',
          opacity: querying || !question.trim() ? 0.6 : 1,
          transition: 'all 0.2s'
        }}
      >
        {querying ? 'Searching...' : 'Search'}
      </button>
    </div>
  );
}
