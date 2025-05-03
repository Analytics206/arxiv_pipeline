import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

function GraphVisualization({ graphData }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize cytoscape
    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': '#6495ED',
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              'color': '#fff',
              'text-outline-width': 2,
              'text-outline-color': '#6495ED'
            }
          },
          {
            selector: 'node[type="Paper"]',
            style: {
              'background-color': '#6495ED',
              'shape': 'rectangle'
            }
          },
          {
            selector: 'node[type="Author"]',
            style: {
              'background-color': '#FF7F50',
              'shape': 'ellipse'
            }
          },
          {
            selector: 'node[type="Category"]',
            style: {
              'background-color': '#32CD32',
              'shape': 'diamond'
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 3,
              'line-color': '#ccc',
              'target-arrow-color': '#ccc',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier'
            }
          }
        ],
        layout: {
          name: 'cose',
          idealEdgeLength: 100,
          nodeOverlap: 20,
          refresh: 20,
          fit: true,
          padding: 30,
          randomize: false,
          componentSpacing: 100,
          nodeRepulsion: 400000,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0
        },
        elements: []
      });
    }

    // Update graph data when it changes
    if (graphData && graphData.nodes && graphData.edges) {
      cyRef.current.elements().remove();
      cyRef.current.add({
        nodes: graphData.nodes,
        edges: graphData.edges
      });
      cyRef.current.layout({ name: 'cose' }).run();
      cyRef.current.fit();
    }

    return () => {
      // No cleanup needed for Cytoscape instance
    };
  }, [graphData]);

  return (
    <div className="graph-container">
      <div ref={containerRef} style={{ width: '100%', height: '500px', border: '1px solid #ddd', borderRadius: '8px' }}></div>
    </div>
  );
}

export default GraphVisualization;