import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import BazelChatViz from './BazelChatViz.jsx'

import { initTelemetry } from './telemetry.js';
initTelemetry();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BazelChatViz />
  </React.StrictMode>,
)
