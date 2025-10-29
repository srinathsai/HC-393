export default function MetricsDisplay({ metrics }) {
  if (!metrics) {
    return null;
  }

  const safeMetrics = {
    total_documents: metrics.total_documents || 0,
    total_nodes: metrics.total_nodes || metrics.nodes || 0,
    total_relationships: metrics.total_relationships || metrics.relationships || 0,
    avg_query_time_ms: metrics.avg_query_time_ms || 0,
    ingestion_rate_docs_per_min: metrics.ingestion_rate_docs_per_min || 0,
    accuracy_score: metrics.accuracy_score || 0
  };

  return (
    <div style={{
      background: '#1e293b',
      padding: '1rem 2rem',
      display: 'flex',
      gap: '2rem',
      borderBottom: '1px solid #334155',
      flexWrap: 'wrap'
    }}>
      <MetricCard label="Documents" value={safeMetrics.total_documents} />
      <MetricCard label="Nodes" value={safeMetrics.total_nodes} />
      {/* HIDDEN FOR DEMO: Relationships */}
      {/* <MetricCard label="Relationships" value={safeMetrics.total_relationships} /> */}
      <MetricCard 
        label="Avg Query Time" 
        value={safeMetrics.avg_query_time_ms > 0 ? `${safeMetrics.avg_query_time_ms.toFixed(0)}ms` : '0ms'} 
      />
      <MetricCard 
        label="Ingestion Rate" 
        value={safeMetrics.ingestion_rate_docs_per_min > 0 ? `${safeMetrics.ingestion_rate_docs_per_min.toFixed(1)}/min` : '0/min'} 
      />
      {/* HIDDEN FOR DEMO: Accuracy */}
      {/* <MetricCard 
        label="Accuracy" 
        value={safeMetrics.accuracy_score > 0 ? `${(safeMetrics.accuracy_score * 100).toFixed(0)}%` : '95%'} 
      /> */}
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginBottom: '0.25rem' }}>
        {label}
      </div>
      <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
        {value}
      </div>
    </div>
  );
}
