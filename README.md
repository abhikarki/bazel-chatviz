# Bazel ChatViz

A local tool for visualizing and chatting with Bazel build data. Analyze build event protocol (BEP) files through an interactive web interface with natural language queries.

## Features

- **Interactive Build Visualization**: Graph-based view of build targets, tests, and dependencies
- **Natural Language Chat**: Ask questions about your build in plain English
- **Build Analysis**: 
  - Failed targets and tests
  - Cache hit/miss analysis
  - Performance metrics
  - Dependency exploration
- **Local & Secure**: All data stays on your machine - no external API calls

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

## Usage Examples

Once running, you can ask questions like:

- **"Show me failed targets"** - Lists all failed build targets
- **"What are the test results?"** - Summary of test passes/failures
- **"Which targets were rebuilt?"** - Shows cache misses and rebuilds
- **"Show build performance summary"** - Execution time analysis
- **"What are the dependencies of //my:target?"** - Dependency graph for specific target
- **"Why was X rebuilt?"** - Analysis of cache misses
- **"Show me the slowest actions"** - Performance bottlenecks

## Architecture

### Backend (Python + FastAPI)
- **BEP Parser**: Extracts targets, actions, tests from build event protocol JSON
- **Chat Engine**: Rule-based NLP for interpreting user queries
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
| `/api/load-bep` | POST | Upload and parse BEP file |
| `/api/graph` | GET | Get build dependency graph data |
| `/api/chat` | POST | Process natural language queries |
| `/api/tests` | GET | Get test results summary |
| `/api/stats` | GET | Get build statistics overview |

### Chat API Example

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "show me failed targets"}'
```

Response:
```json
{
  "answer": "Build failures: 2 targets failed",
  "graph_nodes": [
    {
      "id": "//my:target", 
      "label": "target",
      "type": "target",
      "status": "failed"
    }
  ],
  "metadata": {"failed_targets": ["//my:target", "//other:target"]}
}
```

## Chat Query Patterns

The chat system recognizes these query patterns:

| Pattern | Keywords | Example Queries |
|---------|----------|-----------------|
| Dependencies | `dep`, `depend`, `dependency` | "What depends on //my:lib?" |
| Failures | `fail`, `failed`, `error` | "Show me what failed" |
| Tests | `test`, `testing` | "How many tests passed?" |
| Cache | `cache`, `cached`, `rebuild` | "What was rebuilt?" |
| Performance | `time`, `slow`, `performance` | "What took the longest?" |
| Targets | `target`, `targets` | "List all targets" |
| Summary | `summary`, `overview`, `stats` | "Build summary" |

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

### Adding New Chat Patterns

To add new query patterns, modify the `ChatEngine` class in `backend/main.py`:

```python
def _handle_custom_query(self, question: str) -> ChatResponse:
    """Handle custom query pattern"""
    # Your custom logic here
    return ChatResponse(answer="Custom response")

# Add to patterns list
self.patterns.append(
    (r'.*\bcustom_keyword\b.*', self._handle_custom_query)
)
```

## Generating BEP Files

```bash
# Basic build with BEP
bazel build --build_event_json_file=build.json //...

# Include more detailed information
bazel build \
  --build_event_json_file=build.json \
  --build_event_publish_all_actions \
  --experimental_build_event_expand_filesets \
  //your/target:here

# For test runs
bazel test \
  --build_event_json_file=test_build.json \
  --build_event_publish_all_actions \
  //your/test:targets
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   ./bazel-chatviz serve --port 8080 build.json
   ```

2. **BEP file not found**
   ```bash
   # Check file exists
   ls -la build.json
   # Use absolute path
   ./bazel-chatviz serve /full/path/to/build.json
   ```

3. **No build data showing**
   - Ensure BEP file contains actual build events
   - Try rebuilding with `--build_event_publish_all_actions`

4. **Frontend not connecting to backend**
   - Check that both servers are running
   - Verify ports in browser console for CORS errors

### Debug Mode

```bash
# Backend with debug logging
cd backend
python main.py --bep-file ../build.json --port 8000 --debug

# Frontend with detailed errors  
cd frontend
npm run dev -- --debug
```

## Future Enhancements

- **Skyframe Integration**: Parse Skyframe dumps for deeper dependency analysis
- **Advanced Visualizations**: Timeline view, critical path analysis
- **LLM Integration**: Optional local LLM for more sophisticated query understanding
- **Build Comparison**: Compare multiple BEP files to analyze changes
- **Export Features**: Export graphs and analysis reports
- **Real-time Monitoring**: Live build monitoring during execution

## Requirements

- **Python**: 3.8 or higher
- **Node.js**: 16 or higher  
- **Bazel**: Any recent version (for generating BEP files)
- **Browser**: Modern browser with JavaScript enabled

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

**Bazel ChatViz** - Making build analysis as easy as having a conversation.