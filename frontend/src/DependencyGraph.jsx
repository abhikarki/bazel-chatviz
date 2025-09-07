import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const DependencyGraph = () => {
  const [graphData, setGraphData] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/graph')
      .then(response => response.json())
      .then(data => {
        console.log('Graph data:', data);
        setGraphData(data);
      })
      .catch(error => console.error('Error fetching graph data:', error));
  }, []);

  useEffect(() => {
    if (!graphData) return;

    const width = 800;
    const height = 600;

    // Clear old svg
    d3.select(containerRef.current).selectAll('*').remove();

    const svg = d3.select(containerRef.current)
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    const simulation = d3.forceSimulation(graphData.nodes)
      .force('link', d3.forceLink(graphData.edges).id(d => d.id))
      .force('charge', d3.forceManyBody().strength(-100))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
      .selectAll('line')
      .data(graphData.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6);

    const node = svg.append('g')
      .selectAll('circle')
      .data(graphData.nodes)
      .enter()
      .append('circle')
      .attr('r', 5)
      .attr('fill', d => {
        switch (d.type) {
          case 'target': return d.status === 'success' ? '#4CAF50' : '#f44336';
          case 'test': return d.status === 'passed' ? '#2196F3' : '#FF9800';
          default: return '#9E9E9E';
        }
      });

    const label = svg.append('g')
      .selectAll('text')
      .data(graphData.nodes)
      .enter()
      .append('text')
      .text(d => d.label)
      .attr('font-size', 8)
      .attr('dx', 8)
      .attr('dy', 3);

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);

      label
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });

  }, [graphData]);

 return (
  <div className="w-full bg-white rounded-lg border">
    {/* Graph area */}
    <div
      ref={containerRef}
      id="graph-container"
      className="w-full h-[600px] overflow-auto"
    ></div>

    {/* Metadata area */}
    {graphData && (
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div className="bg-gray-50 p-3 rounded">
          <span className="font-medium">Targets:</span> {graphData.metadata.totalTargets}
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <span className="font-medium">Tests:</span> {graphData.metadata.totalTests}
        </div>
      </div>
    )}
  </div>
);

};


export default DependencyGraph;
