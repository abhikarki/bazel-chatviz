import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

const ResourceGraph = () => {
  const containerRef = useRef();

  useEffect(() => {
    fetchAndRenderData();
  }, []);

  const fetchAndRenderData = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/resource-usage");
      const data = await response.json();
      renderGraphs(data);
    } catch (error) {
      console.error("Error fetching resource data:", error);
    }
  };

  const renderGraphs = (data) => {
    const metrics = [
      { key: "cpu", label: "CPU Usage (%)", color: "#ff4444" },
      { key: "memory", label: "Memory Usage (MB)", color: "#4444ff" },
      // Add more like: { key: "disk", label: "Disk I/O", color: "#00aa88" }
    ];

    // Clear old graphs
    d3.select(containerRef.current).selectAll("*").remove();

    metrics.forEach((metric) => {
      const margin = { top: 30, right: 30, bottom: 40, left: 60 };
      const width = 400 - margin.left - margin.right;
      const height = 250 - margin.top - margin.bottom;

      const svg = d3
        .select(containerRef.current)
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .attr("class", "bg-white shadow rounded-lg")
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      // Scales
      const xScale = d3
        .scaleLinear()
        .domain(d3.extent(data.time))
        .range([0, width]);

      const yScale = d3
        .scaleLinear()
        .domain([0, d3.max(data[metric.key]) * 1.1])
        .range([height, 0]);

      // Line generator
      const line = d3
        .line()
        .x((d, i) => xScale(data.time[i]))
        .y((d) => yScale(d))
        .curve(d3.curveMonotoneX);

      // Path
      svg
        .append("path")
        .datum(data[metric.key])
        .attr("fill", "none")
        .attr("stroke", metric.color)
        .attr("stroke-width", 2)
        .attr("d", line);

      // Axes
      svg
        .append("g")
        .attr("transform", `translate(0,${height})`)
        .call(
          d3
            .axisBottom(xScale)
            .tickFormat((d) => `${(d / 1000).toFixed(1)}s`)
        );

      svg.append("g").call(d3.axisLeft(yScale));

      // Title
      svg
        .append("text")
        .attr("x", width / 2)
        .attr("y", -10)
        .attr("text-anchor", "middle")
        .style("font-size", "12px")
        .style("font-weight", "600")
        .text(metric.label);

      // Tooltip
      const tooltip = d3
        .select(containerRef.current)
        .append("div")
        .style("position", "absolute")
        .style("background", "white")
        .style("border", "1px solid #ddd")
        .style("padding", "6px")
        .style("border-radius", "4px")
        .style("pointer-events", "none")
        .style("opacity", 0);

      const focus = svg
        .append("circle")
        .attr("r", 4)
        .attr("fill", metric.color)
        .style("opacity", 0);

      svg
        .append("rect")
        .attr("width", width)
        .attr("height", height)
        .style("fill", "none")
        .style("pointer-events", "all")
        .on("mousemove", function (event) {
          const [x] = d3.pointer(event);
          const time = xScale.invert(x);
          const idx = d3.bisectCenter(data.time, time);
          tooltip
            .style("opacity", 1)
            .html(
              `<strong>${(data.time[idx] / 1000).toFixed(
                2
              )}s</strong><br/>${metric.label}: ${data[metric.key][
                idx
              ].toFixed(1)}`
            )
            .style("left", `${event.pageX + 10}px`)
            .style("top", `${event.pageY - 30}px`);

          focus
            .attr("cx", xScale(data.time[idx]))
            .attr("cy", yScale(data[metric.key][idx]))
            .style("opacity", 1);
        })
        .on("mouseout", function () {
          tooltip.style("opacity", 0);
          focus.style("opacity", 0);
        });
    });
  };

  return (
    <div
      ref={containerRef}
      className="resource-graph grid grid-cols-2 gap-4 p-4 relative"
    ></div>
  );
};

export default ResourceGraph;
