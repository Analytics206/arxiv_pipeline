import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

const GraphVisualization = ({ graphData }) => {
  const cyRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!graphData || !graphData.nodes || !graphData.edges) return;

    // Clear any existing graph
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Initialize cytoscape with data - NOTE: using spread operator for elements
    const cy = cytoscape({
      container: containerRef.current,
      elements: [...graphData.nodes, ...graphData.edges],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#6FB1FC',
            'label': 'data(label)',
            'width': 50,
            'height': 50,
            'font-size': '12px',
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#fff',
            'text-outline-width': 2,
            'text-outline-color': '#6FB1FC'
          }
        },
        {
          selector: 'node[type="Paper"]',
          style: {
            'background-color': '#E8747C',
            'text-outline-color': '#E8747C',
            'shape': 'rectangle'
          }
        },
        {
          selector: 'node[type="Author"]',
          style: {
            'background-color': '#6FB1FC',
            'text-outline-color': '#6FB1FC',
            'shape': 'ellipse'
          }
        },
        {
          selector: 'node[type="Category"]',
          style: {
            'background-color': '#8BE86B',
            'text-outline-color': '#8BE86B',
            'shape': 'diamond'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 4,
            'line-color': '#888',
            'target-arrow-color': '#888',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'text-background-opacity': 0.6,
            'text-background-color': '#ffffff',
            'text-background-shape': 'roundrectangle',
            'text-background-padding': 2
          }
        }
      ],
      layout: {
        name: 'cose',
        idealEdgeLength: 150,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 50,
        randomize: true,
        componentSpacing: 150,
        nodeRepulsion: 500000,
        edgeElasticity: 150,
        nestingFactor: 5,
        gravity: 100,
        numIter: 1500,
        initialTemp: 250,
        coolingFactor: 0.95,
        minTemp: 1.0
      }
    });

    // Manual resize hack to force full container size
    setTimeout(() => {
      cy.resize();
      cy.fit();
    }, 200);
    
    // Add window resize handler
    const resizeHandler = () => {
      cy.resize();
      cy.fit();
    };
    
    window.addEventListener('resize', resizeHandler);
    
    cyRef.current = cy;

    return () => {
      window.removeEventListener('resize', resizeHandler);
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [graphData]);

  return (
    <div 
      ref={containerRef} 
      className="graph-container" 
      style={{ width: '100%', height: '800px' }}
    ></div>
  );
};

export default GraphVisualization;