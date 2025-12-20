import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Bot, User, Loader2, Upload, File, CheckCircle, AlertTriangle } from 'lucide-react';

const BuildChatbot = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hi! I'm your build analysis assistant. Please upload your BEP file to begin.",
      isBot: true,
      timestamp: new Date()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [fileId, setFileId] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isExpanded) {
        setTimeout(() => fileInputRef.current?.click(), 100);
    }
  }, [isExpanded]);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      handleUpload(file);
    }
  };

  const addMessage = (text, isBot) => {
    setMessages(prev => [
      ...prev,
      { id: prev.length + 1, text, isBot, timestamp: new Date() }
    ]);
  };

  const handleUpload = async (file) => {
    setIsLoading(true);
    setUploadStatus('Initializing...');
    addMessage(`Uploading file: ${file.name}`, false);

    try {
      // 1. Initialize upload
      const initResponse = await fetch('http://localhost:8001/upload/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name })
      });
      if (!initResponse.ok) throw new Error('Initialization failed');
      const { file_id, url } = await initResponse.json();
      setFileId(file_id);

      // 2. Upload file to S3
      setUploadStatus('Uploading...');
      const uploadResponse = await fetch(url, { method: 'PUT', body: file });
      if (!uploadResponse.ok) throw new Error('S3 upload failed');

      // 3. Complete upload
      setUploadStatus('Processing...');
      const completeResponse = await fetch('http://localhost:8001/upload/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id })
      });
      if (!completeResponse.ok) throw new Error('Completion notification failed');

      // 4. Poll for status
      pollForStatus(file_id);

    } catch (error) {
      console.error('Upload error:', error);
      addMessage(`Error: ${error.message}`, true);
      setUploadStatus(null);
      setIsLoading(false);
    }
  };

  const pollForStatus = async (fileId) => {
    const interval = setInterval(async () => {
      try {
        const statusResponse = await fetch(`http://localhost:8001/upload/status/${fileId}`);
        if (!statusResponse.ok) {
            // Stop polling on server error, but don't throw an error,
            // as the server might just be temporarily unavailable.
            console.warn(`Could not fetch status for ${fileId}. Server responded with ${statusResponse.status}.`);
            return;
        }

        const { status, detail } = await statusResponse.json();
        setUploadStatus(`Processing: ${status}`);

        if (status === 'completed') {
          clearInterval(interval);
          addMessage('Processing complete! Here are your artifacts.', true);
          fetchArtifacts(fileId);
          setIsLoading(false);
          setUploadStatus(null);
        } else if (status === 'failed') {
          clearInterval(interval);
          addMessage(`Processing failed: ${detail}`, true);
          setIsLoading(false);
          setUploadStatus(null);
        }
      } catch (error) {
        // Also stop polling on network error
        console.error('Polling error:', error);
        clearInterval(interval);
        addMessage('Error checking status. Please check your connection.', true);
        setIsLoading(false);
        setUploadStatus(null);
      }
    }, 3000);
  };

  const fetchArtifacts = async (fileId) => {
    try {
        const artifactsResponse = await fetch(`http://localhost:8001/upload/artifacts/${fileId}`);
        if (!artifactsResponse.ok) throw new Error('Failed to fetch artifacts');
        const artifacts = await artifactsResponse.json();

        // Create a formatted message with artifact links
        const artifactMessage = "You can view the generated analysis below:\n" +
            Object.entries(artifacts).map(([key, value]) =>
                `* **${key.replace('_url', '')}:** [View](${value})`
            ).join('\n');

        addMessage(artifactMessage, true);
    } catch (error) {
        console.error('Artifact fetch error:', error);
        addMessage('Could not retrieve artifacts.', true);
    }
  };


  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!isExpanded) {
    return (
        <div className="fixed bottom-6 right-6 z-50">
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} style={{ display: 'none' }} accept=".bep" />
            <button
                onClick={() => setIsExpanded(true)}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-full p-4 shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 group flex items-center gap-3 pr-6"
            >
                <Upload size={24} className="flex-shrink-0" />
                <span className="font-medium text-sm whitespace-nowrap">Upload BEP File</span>
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            </button>
        </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 h-[600px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
            <Bot size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Build Assistant</h3>
            <p className="text-xs text-blue-100">Upload your BEP file to start</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(false)}
          className="text-white/80 hover:text-white hover:bg-white/20 rounded-full p-1 transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.isBot ? 'justify-start' : 'justify-end'}`}
          >
            {message.isBot && (
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-white" />
              </div>
            )}
            <div
              className={`max-w-[80%] p-3 rounded-2xl text-sm ${ 
                message.isBot
                  ? 'bg-white text-gray-800 shadow-sm border'
                  : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.text}</p>
              <p className={`text-xs mt-1 ${ 
                message.isBot ? 'text-gray-500' : 'text-blue-100'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>
            {!message.isBot && (
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
                    <File size={16} className="text-gray-600" />
                </div>
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-3 justify-start">
             <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-white" />
            </div>
            <div className="bg-white p-3 rounded-2xl shadow-sm border">
              <div className="flex items-center gap-2 text-gray-500">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">{uploadStatus || 'Analyzing...'}</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-gray-100">
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-4 py-3 flex items-center justify-center transition-all duration-200 hover:shadow-lg"
        >
          <Upload size={16} className="mr-2" />
          <span>{isLoading ? 'Processing...' : 'Upload another BEP File'}</span>
        </button>
         <input type="file" ref={fileInputRef} onChange={handleFileSelect} style={{ display: 'none' }} accept=".bep" />

      </div>
    </div>
  );
};

export default BuildChatbot;
