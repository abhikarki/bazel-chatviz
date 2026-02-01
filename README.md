# Bazel ChatViz
### Making build analysis as easy as having a conversation.
 A distributed build analysis platform for processing Bazel Event Protocol(BEP) files and natural language queries for build performance analysis and debugging.

[comment]: # (https://github.com/user-attachments/assets/617d93b3-2322-4a0c-a770-49f3be662ace)

## System Design
<img width="1904" height="886" alt="bazel-system-diagram-LGTM" src="https://github.com/user-attachments/assets/66567f36-6021-4dd9-98b5-680cf2faadd2" />

## Features

- **Interactive Build Visualization**: Graph-based view of build targets, tests, and dependencies
- **Natural Language Chat**: Ask questions about your build in plain English
- **Build Analysis**: 
  - Failed targets and tests
  - Cache hit/miss analysis
  - Performance metrics
  - Dependency exploration

### Guide

### 1. Generate BEP File

```bash
# Run your Bazel build with BEP output
bazel build --build_event_json_file=build.json //your/target:here
```



#### Running local vector database
```bash
 docker run -d -p 8080:8080 `
  -e QUERY_DEFAULTS_LIMIT=20 `
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true `
  semitechnologies/weaviate:latest
```


## License

MIT License - see LICENSE file for details.

---
