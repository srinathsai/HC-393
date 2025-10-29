import ForceGraph2D from 'react-force-graph-2d';

export default function GraphVisualization({ graphData }) {
  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '0.75rem',
      padding: '1.5rem',
      boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
    }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        🕸️ Knowledge Graph
      </h2>

      <div style={{
        width: '100%',
        height: '600px',
        background: '#0f172a',
        borderRadius: '0.5rem',
        overflow: 'hidden',
        border: '1px solid #334155'
      }}>
        {graphData && graphData.nodes && graphData.nodes.length > 0 ? (
          <ForceGraph2D
            graphData={graphData}
            nodeLabel="name"
            nodeColor={node => {
              if (node.type === 'Component') return '#f59e0b';
              if (node.type === 'Location') return '#3b82f6';
              if (node.type === 'Drawing') return '#8b5cf6';
              return '#64748b';
            }}
            linkColor={() => '#64748b'}
            linkWidth={2}
            nodeRelSize={6}
            backgroundColor="#0f172a"
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              
              // Node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
              ctx.fillStyle = node.color || '#64748b';
              ctx.fill();
              
              // Label
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = '#e2e8f0';
              ctx.fillText(label, node.x, node.y + 10);
            }}
          />
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            opacity: 0.5,
            textAlign: 'center',
            padding: '2rem',
            flexDirection: 'column',
            gap: '1rem'
          }}>
            <div style={{ fontSize: '3rem' }}>🕸️</div>
            <div>
              <p style={{ marginBottom: '0.5rem' }}>No graph data available</p>
              <p style={{ fontSize: '0.875rem', opacity: 0.7 }}>
                Upload documents and run queries to see the knowledge graph
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
