# Bazel ChatViz
### Making build analysis as easy as having a conversation.

A local tool for visualizing and chatting with Bazel build data. Analyze build event protocol (BEP) files through an interactive web interface with natural language queries.


https://github.com/user-attachments/assets/617d93b3-2322-4a0c-a770-49f3be662ace

## System Design
<img width="1294" height="789" alt="bazel_sys_design_v1" src="https://github.com/user-attachments/assets/0ff80680-0494-4022-a8e2-23e11c2fd4ba" />

## Features

- **Interactive Build Visualization**: Graph-based view of build targets, tests, and dependencies
- **Natural Language Chat**: Ask questions about your build in plain English
- **Build Analysis**: 
  - Failed targets and tests
  - Cache hit/miss analysis
  - Performance metrics
  - Dependency exploration
- **Local & Secure**

### Guide

### 1. Generate BEP File

```bash
# Run your Bazel build with BEP output
bazel build --build_event_json_file=build.json //your/target:here
```

### 2. Start ChatViz

```bash
# Start with BEP file
./bazel-chatviz serve build.json

# Or start and upload file via UI
./bazel-chatviz serve
```

## Architecture

### Backend (Python + FastAPI)
- **BEP Parser**: Extracts targets, actions, tests from build event protocol JSON
- **ChatBot**: RAG pipeline for context based Chat queries
- **REST API**: Serves build data and handles chat queries
- **Graph Generator**: Creates dependency graphs for visualization

### Frontend (React + Vite)
- **File Upload**: Drag & drop BEP file interface
- **Graph Visualization**: Interactive build dependency graphs
- **Chat Interface**: Natural language query input with suggestions
- **Statistics Dashboard**: Build metrics and summaries


## CLI Usage

```bash
# Basic usage
./bazel-chatviz serve [BEP_FILE]

# Options
./bazel-chatviz serve --port 8080 build.json    # Custom port
./bazel-chatviz serve --no-browser build.json   # Don't open browser
./bazel-chatviz serve --backend-only build.json # Only start API server
./bazel-chatviz serve --frontend-only           # Only start frontend

# Help
./bazel-chatviz --help
```

## API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/graph` | GET | Get build dependency graph data |
| `/api/query` | POST | Process natural language queries for chatbot |
| `/api/resource-usage` | GET | Get the resource usage graphs |
\```

## Development

### Running Backend Only
```bash
cd backend
python main.py --bep-file ../build.json --port 8000
```

### Running Frontend Only
```bash
cd frontend
npm run dev
```


## Future Enhancements

- **Skyframe Integration**: Parse Skyframe dumps for deeper dependency analysis
- **Build Comparison**: Compare multiple BEP files to analyze changes
- **Real-time Monitoring**: Live build monitoring during execution


## License

MIT License - see LICENSE file for details.

---
