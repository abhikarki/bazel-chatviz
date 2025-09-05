import React, { useState, useEffect, useCallback } from 'react';
import { Upload, Send, MessageCircle, BarChart3, Network, TestTube, Settings, FileText, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import * as d3 from 'd3';

import ResourceGraph from './ResourceGraph';

const API_BASE = 'http://localhost:8000/api';




const BuildGraph = () => {
  const [graphData, setGraphData] = useState(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/graph')
      .then(response => response.json())
      .then(data => {
        console.log('Graph data:', data); // Debug log
        setGraphData(data);
        if (data.nodes.length > 0) {
          renderGraph(data);
        }
      })
      .catch(error => console.error('Error fetching graph data:', error));
  }, []);

  const renderGraph = (data) => {
    const width = 800;
    const height = 600;

    // Clear any existing SVG
    d3.select('#graph-container').selectAll('*').remove();

    const svg = d3.select('#graph-container')
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    // Create force simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id(d => d.id))
      .force('charge', d3.forceManyBody().strength(-100))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Add links
    const link = svg.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6);

    // Add nodes
    const node = svg.append('g')
      .selectAll('circle')
      .data(data.nodes)
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

    // Add labels
    const label = svg.append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text(d => d.label)
      .attr('font-size', 8)
      .attr('dx', 8)
      .attr('dy', 3);

    // Update positions on simulation tick
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
  };

   return (
    <div>
      <h2>Build Dependency Graph</h2>
      <div id="graph-container"></div>
      {graphData && (
        <div className="graph-stats">
          <p>Targets: {graphData.metadata.totalTargets}</p>
          <p>Tests: {graphData.metadata.totalTests}</p>
        </div>
      )}
    </div>
  );
};



// Graph visualization component using D3.js concepts with React
const GraphVisualization = ({ nodes, edges, selectedNode, onNodeClick }) => {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !nodes || nodes.length === 0) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500 text-center">
          <Network className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No graph data available</p>
          <p className="text-sm">Load a BEP file to visualize build dependencies</p>
        </div>
      </div>
    );
  }

  const getNodeColor = (status, type) => {
    if (type === 'test') {
      return status === 'success' ? 'bg-green-500' : 'bg-red-500';
    }
    if (status === 'success') return 'bg-blue-500';
    if (status === 'failed') return 'bg-red-500';
    if (status === 'cached') return 'bg-yellow-500';
    return 'bg-gray-400';
  };

  const getNodeIcon = (type) => {
    switch (type) {
      case 'test': return <TestTube className="w-4 h-4" />;
      case 'action': return <Settings className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  return (
    <div className="w-full h-96 bg-gray-50 rounded-lg p-4 overflow-auto">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {nodes.slice(0, 24).map((node, index) => (
          <div
            key={node.id}
            onClick={() => onNodeClick && onNodeClick(node)}
            className={`
              p-3 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-md
              ${selectedNode?.id === node.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}
            `}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className={`p-1 rounded ${getNodeColor(node.status, node.type)} text-white`}>
                {getNodeIcon(node.type)}
              </div>
              <span className="font-medium text-sm truncate flex-1">{node.label}</span>
            </div>
            <div className="text-xs text-gray-600">
              <div className="flex justify-between">
                <span className="capitalize">{node.type}</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  node.status === 'success' ? 'bg-green-100 text-green-800' :
                  node.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {node.status}
                </span>
              </div>
              {node.execution_time && (
                <div className="mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{node.execution_time.toFixed(2)}s</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {nodes.length > 24 && (
        <div className="mt-4 text-center text-gray-500 text-sm">
          Showing first 24 of {nodes.length} nodes
        </div>
      )}
    </div>
  );
};

const ChatInterface = ({ onSendMessage, messages, isLoading }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const suggestions = [
    "Show me failed targets",
    "What are the test results?", 
    "Show build performance summary",
    "Which targets were rebuilt?",
    "Show me the dependency graph"
  ];

  return (
    <div className="flex flex-col h-96">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-4 mb-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-gray-500 text-center">
            <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Ask me about your Bazel build!</p>
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium">Try asking:</p>
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setInput(suggestion)}
                  className="block w-full text-left text-sm bg-white px-3 py-2 rounded border hover:bg-gray-50 transition-colors"
                >
                  "{suggestion}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`
                max-w-3/4 px-4 py-2 rounded-lg
                ${message.type === 'user' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-white text-gray-800 border border-gray-200'
                }
              `}>
                <p>{message.content}</p>
                {message.metadata && (
                  <div className="mt-2 text-xs opacity-75">
                    <pre className="whitespace-pre-wrap">
                      {JSON.stringify(message.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 border border-gray-200 px-4 py-2 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                <span>Analyzing build data...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your build... (e.g., 'Show me failed targets')"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};

const StatsPanel = ({ stats }) => {
  if (!stats) return null;

  const items = [
    {
      label: 'Targets',
      value: `${stats.successful_targets || 0}/${stats.targets || 0}`,
      icon: FileText,
      color: 'blue',
      success: (stats.successful_targets || 0) === (stats.targets || 0)
    },
    {
      label: 'Tests',
      value: `${stats.passed_tests || 0}/${stats.tests || 0}`,
      icon: TestTube,
      color: 'green',
      success: (stats.passed_tests || 0) === (stats.tests || 0)
    },
    {
      label: 'Actions',
      value: stats.actions || 0,
      icon: Settings,
      color: 'purple'
    }
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
      {items.map((item, index) => (
        <div key={index} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">{item.label}</p>
              <p className="text-2xl font-bold text-gray-900">{item.value}</p>
            </div>
            <div className={`p-2 rounded-lg ${
              item.success === true ? 'bg-green-100 text-green-600' :
              item.success === false ? 'bg-red-100 text-red-600' :
              `bg-${item.color}-100 text-${item.color}-600`
            }`}>
              {item.success === true ? (
                <CheckCircle className="w-6 h-6" />
              ) : item.success === false ? (
                <AlertCircle className="w-6 h-6" />
              ) : (
                <item.icon className="w-6 h-6" />
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const FileUploader = ({ onFileUpload, isUploading, hasData }) => {
  const [dragActive, setDragActive] = useState(false);
  
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  }, [onFileUpload]);

  const handleChange = useCallback((e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      onFileUpload(e.target.files[0]);
    }
  }, [onFileUpload]);

  return (
    <div className="mb-6">
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center transition-colors
          ${dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'}
          ${hasData ? 'bg-green-50 border-green-300' : ''}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-gray-400'}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".json,.jsonl"
          onChange={handleChange}
          disabled={isUploading}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        
        <div className="space-y-2">
          <Upload className={`
            w-10 h-10 mx-auto 
            ${hasData ? 'text-green-500' : dragActive ? 'text-blue-500' : 'text-gray-400'}
          `} />
          
          {isUploading ? (
            <div className="space-y-2">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-gray-600">Uploading and parsing BEP file...</p>
            </div>
          ) : hasData ? (
            <div className="space-y-1">
              <p className="text-sm font-medium text-green-600">✓ BEP file loaded successfully</p>
              <p className="text-xs text-gray-500">Drop another file to reload, or start chatting below</p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-sm font-medium text-gray-700">
                Drop your BEP JSON file here or click to browse
              </p>
              <p className="text-xs text-gray-500">
                Supports .json and .jsonl files from bazel build --build_event_json_file
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const BazelChatViz = () => {
  const [stats, setStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchGraph = async () => {
    try {
      const response = await fetch(`${API_BASE}/graph`);
      if (response.ok) {
        const data = await response.json();
        setGraphData(data);
      }
    } catch (error) {
      console.error('Failed to fetch graph:', error);
    }
  };

  const handleFileUpload = async (file) => {
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE}/load-bep`, {
        method: 'POST',
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        setMessages([{
          type: 'system',
          content: `✓ ${result.message}. Found ${result.stats.targets} targets, ${result.stats.actions} actions, and ${result.stats.tests} tests.`,
          metadata: result.stats
        }]);
        
        // Refresh data
        await fetchStats();
        await fetchGraph();
      } else {
        const error = await response.json();
        setMessages([{
          type: 'system',
          content: `❌ Failed to load file: ${error.detail}`,
        }]);
      }
    } catch (error) {
      setMessages([{
        type: 'system',
        content: `❌ Error uploading file: ${error.message}`,
      }]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (message) => {
    // Add user message
    const userMessage = { type: 'user', content: message };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: message }),
      });

      if (response.ok) {
        const result = await response.json();
        
        // Add assistant response
        const assistantMessage = {
          type: 'assistant',
          content: result.answer,
          metadata: result.metadata
        };
        setMessages(prev => [...prev, assistantMessage]);

        // Update graph if new data provided
        if (result.graph_nodes) {
          setGraphData({
            nodes: result.graph_nodes,
            edges: result.graph_edges || []
          });
          setActiveTab('graph'); // Switch to graph view
        }
      } else {
        const error = await response.json();
        setMessages(prev => [...prev, {
          type: 'system',
          content: `❌ Error: ${error.detail}`
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'system',
        content: `❌ Network error: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    // Could trigger additional queries about this node
    handleSendMessage(`Tell me more about ${node.label}`);
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'graph', label: 'Graph', icon: Network },
    { id: 'chat', label: 'Chat', icon: MessageCircle },
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Bazel ChatViz</h1>
          <p className="text-gray-600">Visualize and chat with your Bazel builds</p>
        </div>

        {/* <BuildGraph /> */}

         <ResourceGraph />

        {/* File Upload */}
        <FileUploader 
          onFileUpload={handleFileUpload}
          isUploading={isUploading}
          hasData={stats !== null}
        />

        {/* Stats Panel */}
        <StatsPanel stats={stats} />

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="border-b border-gray-200">
            <nav className="flex">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-6 py-3 font-medium text-sm border-b-2 transition-colors
                    ${activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                    }
                  `}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Build Overview</h3>
                  {stats ? (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Total Targets:</span> {stats.targets}
                        </div>
                        <div>
                          <span className="font-medium">Successful Targets:</span> {stats.successful_targets}
                        </div>
                        <div>
                          <span className="font-medium">Total Tests:</span> {stats.tests}
                        </div>
                        <div>
                          <span className="font-medium">Passed Tests:</span> {stats.passed_tests}
                        </div>
                        <div>
                          <span className="font-medium">Actions Executed:</span> {stats.actions}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500">Load a BEP file to see build statistics</p>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'graph' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Build Graph</h3>
                <GraphVisualization
                  nodes={graphData.nodes}
                  edges={graphData.edges}
                  selectedNode={selectedNode}
                  onNodeClick={handleNodeClick}
                />
                {selectedNode && (
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-medium text-blue-900">Selected: {selectedNode.label}</h4>
                    <div className="text-sm text-blue-700 mt-1">
                      <div>Type: {selectedNode.type}</div>
                      <div>Status: {selectedNode.status}</div>
                      {selectedNode.execution_time && (
                        <div>Execution Time: {selectedNode.execution_time}s</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'chat' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Chat with Your Build</h3>
                <ChatInterface
                  onSendMessage={handleSendMessage}
                  messages={messages}
                  isLoading={isLoading}
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-500 text-sm">
          <p>Bazel ChatViz - Local build analysis tool</p>
          <p>Upload a BEP JSON file generated with: <code className="bg-gray-200 px-1 rounded">bazel build --build_event_json_file=build.json //...</code></p>
        </div>
      </div>
    </div>
  );
};

export default BazelChatViz;