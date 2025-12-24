# Bazel ChatViz
### Making build analysis as easy as having a conversation.
 A distributed build analysis platform for processing Bazel Event Protocol(BEP) files and natural language queries for build performance analysis and debugging.

https://github.com/user-attachments/assets/617d93b3-2322-4a0c-a770-49f3be662ace

## System Design
<img width="1260" height="928" alt="bazel_sys_design_v1img" src="https://github.com/user-attachments/assets/0e07adc0-c16b-40c2-bc98-77b0bc091b98" />


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
