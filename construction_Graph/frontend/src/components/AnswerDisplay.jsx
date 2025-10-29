export default function AnswerDisplay({ answer }) {
  if (!answer) {
    return null;
  }

  const queryType = answer.query_type || 'general';
  const executionTime = answer.execution_time_ms || 0;
  const answerText = answer.answer || 'No answer available';
  const sources = answer.sources || [];

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '0.75rem',
      padding: '1.5rem',
      boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
    }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        💡 Answer
      </h2>

      <div style={{
        padding: '1rem',
        background: '#0f172a',
        borderRadius: '0.5rem',
        borderLeft: '4px solid #8b5cf6'
      }}>
        <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
          {answerText}
        </p>
      </div>

      <div style={{
        marginTop: '1rem',
        display: 'flex',
        gap: '1rem',
        fontSize: '0.875rem',
        opacity: 0.8
      }}>
        <span>Type: {queryType}</span>
        <span>•</span>
        <span>Time: {executionTime.toFixed(0)}ms</span>
      </div>

      {sources.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <p style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Sources:</p>
          {sources.slice(0, 5).map((source, i) => (
            <div key={i} style={{
              padding: '0.5rem',
              background: '#334155',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              marginTop: '0.5rem'
            }}>
              {source.is_diagram ? '🔧' : '📄'} {source.filename || 'Unknown'} - Page {source.page || 0}
              {source.score && ` (Score: ${source.score.toFixed(2)})`}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
