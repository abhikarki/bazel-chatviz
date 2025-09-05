import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const ResourceGraph = () => {
  const svgRef = useRef();

  useEffect(() => {
    fetchAndRenderData();
  }, []);

  const fetchAndRenderData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/resource-usage');
      const data = await response.json();
      renderGraph(data);
    } catch (error) {
      console.error('Error fetching resource data:', error);
    }
  };

  const renderGraph = (data) => {
    const margin = { top: 30, right: 50, bottom: 40, left: 60 };
    const width = 900 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    // Clear old
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const xScale = d3.scaleLinear()
      .domain(d3.extent(data.time))
      .range([0, width]);

    const yMax = Math.max(d3.max(data.cpu), d3.max(data.memory));
    const yScale = d3.scaleLinear()
      .domain([0, yMax * 1.1]) // add padding
      .range([height, 0]);

    // Line generators
    const lineGen = (yScale) => d3.line()
      .x((d, i) => xScale(data.time[i]))
      .y((d) => yScale(d))
      .curve(d3.curveMonotoneX);

    const cpuLine = lineGen(yScale);
    const memoryLine = lineGen(yScale);

    // Area shading for CPU
    svg.append('path')
      .datum(data.cpu)
      .attr('fill', 'rgba(255,68,68,0.15)')
      .attr('stroke', 'none')
      .attr('d', d3.area()
        .x((d, i) => xScale(data.time[i]))
        .y0(height)
        .y1((d) => yScale(d))
      );

    // CPU line
    svg.append('path')
      .datum(data.cpu)
      .attr('fill', 'none')
      .attr('stroke', '#ff4444')
      .attr('stroke-width', 2)
      .attr('d', cpuLine);

    // Memory line
    svg.append('path')
      .datum(data.memory)
      .attr('fill', 'none')
      .attr('stroke', '#4444ff')
      .attr('stroke-width', 2)
      .attr('d', memoryLine);

    // Axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(
        d3.axisBottom(xScale).tickFormat((d) => `${(d / 1000).toFixed(1)}s`)
      );

    svg.append('g').call(d3.axisLeft(yScale));

    // Tooltip
    const tooltip = d3
      .select('.resource-graph')
      .append('div')
      .style('position', 'absolute')
      .style('background', 'white')
      .style('border', '1px solid #ddd')
      .style('padding', '6px')
      .style('border-radius', '4px')
      .style('pointer-events', 'none')
      .style('opacity', 0);

    const focus = svg.append('circle')
      .attr('r', 4)
      .attr('fill', 'blue')
      .style('opacity', 0);

    svg
      .append('rect')
      .attr('width', width)
      .attr('height', height)
      .style('fill', 'none')
      .style('pointer-events', 'all')
      .on('mousemove', function (event) {
        const [x] = d3.pointer(event);
        const time = xScale.invert(x);
        const idx = d3.bisectCenter(data.time, time);
        tooltip
          .style('opacity', 1)
          .html(
            `<strong>${(data.time[idx] / 1000).toFixed(2)}s</strong><br/>
             CPU: ${data.cpu[idx].toFixed(1)}%<br/>
             Memory: ${data.memory[idx].toFixed(1)} MB`
          )
          .style('left', `${event.pageX + 10}px`)
          .style('top', `${event.pageY - 30}px`);

        focus
          .attr('cx', xScale(data.time[idx]))
          .attr('cy', yScale(data.memory[idx]))
          .style('opacity', 1);
      })
      .on('mouseout', function () {
        tooltip.style('opacity', 0);
        focus.style('opacity', 0);
      });

    // Legend
    const legend = svg.append('g')
      .attr('transform', `translate(${width - 120},10)`);

    const items = [
      { color: '#ff4444', label: 'CPU Usage' },
      { color: '#4444ff', label: 'Memory Usage' },
    ];

    items.forEach((item, i) => {
      const g = legend.append('g').attr('transform', `translate(0,${i * 20})`);
      g.append('rect').attr('width', 12).attr('height', 12).attr('fill', item.color);
      g.append('text').attr('x', 20).attr('y', 10).text(item.label).style('font-size', '12px');
    });
  };

  return (
    <div className="resource-graph relative">
      <h2 className="text-lg font-semibold mb-2">Build Resource Usage</h2>
      <svg ref={svgRef}></svg>
    </div>
  );
};

export default ResourceGraph;
