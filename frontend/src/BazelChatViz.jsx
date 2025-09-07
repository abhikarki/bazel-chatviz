import React, { useState, useEffect, useCallback } from 'react';
import { Upload, Send, MessageCircle, BarChart3, Network, TestTube, Settings, FileText, AlertCircle, CheckCircle, Clock, TrendingUp, Activity } from 'lucide-react';
import * as d3 from 'd3';
import ResourceGraph from "./ResourceGraph"
import DependencyGraph from './DependencyGraph';

const API_BASE = 'http://localhost:8000/api';


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
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-4 mb-4 space-y-3 min-h-96">
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

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your build... (e.g., 'Show me failed targets')"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

const CompactFileUploader = ({ onFileUpload, isUploading, hasData }) => {
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
    <div
      className={`
        relative border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer
        ${dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'}
        ${hasData ? 'bg-green-50 border-green-300' : ''}
        ${isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-gray-400'}
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
      
      <div className="flex items-center gap-3">
        <Upload className={`
          w-6 h-6
          ${hasData ? 'text-green-500' : dragActive ? 'text-blue-500' : 'text-gray-400'}
        `} />
        
        {isUploading ? (
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
            <span className="text-sm text-gray-600">Uploading...</span>
          </div>
        ) : hasData ? (
          <div className="text-left">
            <p className="text-sm font-medium text-green-600">✓ BEP loaded</p>
            <p className="text-xs text-gray-500">Drop new file to reload</p>
          </div>
        ) : (
          <div className="text-left">
            <p className="text-sm font-medium text-gray-700">Upload BEP file</p>
            <p className="text-xs text-gray-500">JSON or JSONL format</p>
          </div>
        )}
      </div>
    </div>
  );
};

const StatsOverview = ({ stats }) => {
  if (!stats) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-500">
        <div className="text-center">
          <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>Load a BEP file to see build statistics</p>
        </div>
      </div>
    );
  }

  const items = [
    {
      label: 'Targets',
      value: stats.targets || 0,
      success: stats.successful_targets || 0,
      icon: FileText,
      color: 'blue'
    },
    {
      label: 'Tests',
      value: stats.tests || 0,
      success: stats.passed_tests || 0,
      icon: TestTube,
      color: 'green'
    },
    {
      label: 'Actions',
      value: stats.actions || 0,
      icon: Settings,
      color: 'purple'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {items.map((item, index) => (
          <div key={index} className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{item.label}</p>
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-2xl font-bold text-gray-900">{item.value}</p>
                  {item.success !== undefined && (
                    <span className="text-sm text-gray-500">
                      ({item.success} successful)
                    </span>
                  )}
                </div>
                {item.success !== undefined && (
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        item.success === item.value ? 'bg-green-500' : 'bg-yellow-500'
                      }`}
                      style={{ width: `${(item.success / item.value) * 100}%` }}
                    ></div>
                  </div>
                )}
              </div>
              <div className={`p-3 rounded-lg bg-${item.color}-100 text-${item.color}-600`}>
                <item.icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Build Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Targets:</span>
              <span className="font-medium">{stats.targets}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Successful Targets:</span>
              <span className="font-medium text-green-600">{stats.successful_targets}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Failed Targets:</span>
              <span className="font-medium text-red-600">{(stats.targets || 0) - (stats.successful_targets || 0)}</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Tests:</span>
              <span className="font-medium">{stats.tests}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Passed Tests:</span>
              <span className="font-medium text-green-600">{stats.passed_tests}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Actions Executed:</span>
              <span className="font-medium">{stats.actions}</span>
            </div>
          </div>
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
        
        const assistantMessage = {
          type: 'assistant',
          content: result.answer,
          metadata: result.metadata
        };
        setMessages(prev => [...prev, assistantMessage]);

        if (result.graph_nodes) {
          setGraphData({
            nodes: result.graph_nodes,
            edges: result.graph_edges || []
          });
          setActiveTab('dependency-graph');
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
    handleSendMessage(`Tell me more about ${node.label}`);
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'dependency-graph', label: 'Dependency Graph', icon: Network },
    { id: 'performance', label: 'Resource Usage', icon: TrendingUp },
    { id: 'chat', label: 'Chat', icon: MessageCircle },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-6">
        {/* Header with compact upload */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Bazel ChatViz</h1>
            <p className="text-gray-600">Visualize and chat with your Bazel builds</p>
          </div>
          <div className="w-80">
            <CompactFileUploader 
              onFileUpload={handleFileUpload}
              isUploading={isUploading}
              hasData={stats !== null}
            />
          </div>
        </div>

        {/* Main content with tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          {/* Tab navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-2 px-6 py-4 font-medium text-sm border-b-2 transition-colors whitespace-nowrap
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

          {/* Tab content */}
          <div className="p-6 min-h-[500px]">
            {activeTab === 'overview' && (
              <StatsOverview stats={stats} />
            )}

            {activeTab === 'dependency-graph' && (
              <div className="h-full">
                <DependencyGraph />
              </div>
            )}

            {activeTab === 'performance' && (
              <div className="h-full">
                <ResourceGraph />
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="h-full">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Chat with Your Build</h3>
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
          <p>Generate BEP files with: <code className="bg-gray-200 px-2 py-1 rounded">bazel build --build_event_json_file=build.json //...</code></p>
        </div>
      </div>
    </div>
  );
};

export default BazelChatViz;