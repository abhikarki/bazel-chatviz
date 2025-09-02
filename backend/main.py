import json
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


class ChatRequest(BaseModel):
    question: str
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    answer: str
    graph_nodes: Optional[List[Dict]] = None
    graph_edges: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    status: str
    execution_time: Optional[float] = None
    metadata: Optional[Dict] = None

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str

@dataclass
class BazelTarget:
    name: str
    status: str
    execution_time: float = 0.0
    cache_result: str = "unknown"
    test_result: Optional[str] = None
    dependencies: List[str] = None
    outputs: List[str] = None

    def _post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.outputs is None:
            self.outputs = []

class BEPParser:
    
    def __init__(self):
        self.targets: Dict[str, BazelTarget] = {}
        self.actions: Dict[str, Dict] = {}
        self.test_results: Dict[str, Dict] = {}
        self.build_metadata: Dict = {}

    def parse_file(self, bep_file_path: str) -> None:
        if not os.path.exists(bep_file_path):
            raise FileNotFoundError(f"BEP file not found: {bep_file_path}")
        
        with open(bep_file_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        self._process_event(event)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse BEP line: {e}")
                        continue


    def _process_event(self, event: Dict) -> None:
        event_id = event.get('id', {})

        if 'targetCompleted' in event_id:
            self._process_target_completed(event_id['targetCompleted'])
        elif 'actionExecuted' in event_id:
            self._process_action_executed(event_id['actionExecuted'])
        elif 'testResult' in event_id:
            self._process_test_result(event_id['testResult'])
        elif 'buildMetadata' in event_id:
            self._process_build_metadata(event_id['buildMetadata'])
        # elif 'targetConfigured' in event_id:
        #     # Optional: track configured targets if needed
        #     self._process_target_configured(event_id['targetConfigured'])

    def _process_target_completed(self, target_completed: Dict) -> None:
        target_label = target_completed.get('label', 'unknown')
        success = target_completed.get('success', False)

        self.targets[target_label] = BazelTarget(
            name=target_label,
            status='success' if success else 'failed'
        )
    
    def _process_action_executed(self, event: Dict) -> None:
        """Process action execution event"""
        action = event.get('actionExecuted', {})
        action_id = str(action.get('label', 'unknown'))
        
        self.actions[action_id] = {
            'status': 'success' if action.get('success', False) else 'failed',
            'execution_time': action.get('executionTimeInMs', 0) / 1000.0,
            'cache_result': action.get('cacheResult', 'unknown'),
            'mnemonic': action.get('type', 'unknown')
        }
    
    def _process_test_result(self, event: Dict) -> None:
        """Process test result event"""
        test_result = event.get('testResult', {})
        test_label = test_result.get('label', 'unknown')
        
        self.test_results[test_label] = {
            'status': test_result.get('status', 'unknown'),
            'execution_time': test_result.get('executionTimeInMs', 0) / 1000.0,
            'passed': test_result.get('testResult', {}).get('status') == 'PASSED'
        }
    
    def _process_build_metadata(self, event: Dict) -> None:
        """Process build metadata"""
        self.build_metadata = event.get('buildMetadata', {})

class ChatEngine:
    """Rule-based chat engine for Bazel build queries"""
    
    def __init__(self, bep_parser: BEPParser):
        self.bep_parser = bep_parser
        
        # Define query patterns and handlers
        self.patterns = [
            (r'.*\b(dep|depend|dependency|dependencies)\b.*', self._handle_dependencies),
            (r'.*\b(fail|failed|error)\b.*', self._handle_failures),
            (r'.*\b(test|testing)\b.*', self._handle_tests),
            (r'.*\b(cache|cached|rebuild|rebuilt)\b.*', self._handle_cache),
            (r'.*\b(time|slow|performance)\b.*', self._handle_performance),
            (r'.*\b(target|targets)\b.*', self._handle_targets),
            (r'.*\b(summary|overview|stats)\b.*', self._handle_summary),
        ]
    
    def query(self, question: str) -> ChatResponse:
        """Process natural language query"""
        question_lower = question.lower().strip()
        
        # Try to match patterns
        for pattern, handler in self.patterns:
            if re.match(pattern, question_lower):
                return handler(question)
        
        # Default response
        return ChatResponse(
            answer="I can help you analyze your Bazel build. Try asking about dependencies, failures, tests, cache hits/misses, or performance.",
            metadata={"suggestions": [
                "Show me failed targets",
                "What are the dependencies of //my:target?",
                "Which tests failed?",
                "Why was X rebuilt?",
                "Show build performance summary"
            ]}
        )
    
    def _handle_dependencies(self, question: str) -> ChatResponse:
        """Handle dependency-related queries"""
        # Extract target name if mentioned
        target_match = re.search(r'//[a-zA-Z0-9_/:-]+', question)
        
        nodes = []
        edges = []
        answer = ""
        
        if target_match:
            target = target_match.group(0)
            if target in self.bep_parser.targets:
                # Create dependency graph for specific target
                nodes.append({
                    "id": target,
                    "label": target.split("/")[-1],
                    "type": "target",
                    "status": self.bep_parser.targets[target].status
                })
                answer = f"Showing dependencies for {target}"
            else:
                answer = f"Target {target} not found in build data"
        else:
            # Show all targets and their relationships
            for target_name, target in self.bep_parser.targets.items():
                nodes.append({
                    "id": target_name,
                    "label": target_name.split("/")[-1],
                    "type": "target",
                    "status": target.status
                })
            answer = f"Found {len(nodes)} targets in build"
        
        return ChatResponse(
            answer=answer,
            graph_nodes=nodes,
            graph_edges=edges
        )
    
    def _handle_failures(self, question: str) -> ChatResponse:
        """Handle failure-related queries"""
        failed_targets = [name for name, target in self.bep_parser.targets.items() 
                         if target.status == 'failed']
        failed_actions = [action_id for action_id, action in self.bep_parser.actions.items()
                         if action['status'] == 'failed']
        failed_tests = [test_id for test_id, test in self.bep_parser.test_results.items()
                       if not test.get('passed', True)]
        
        total_failures = len(failed_targets) + len(failed_actions) + len(failed_tests)
        
        if total_failures == 0:
            return ChatResponse(answer="Great news! No failures found in this build.")
        
        answer_parts = []
        if failed_targets:
            answer_parts.append(f"{len(failed_targets)} targets failed")
        if failed_actions:
            answer_parts.append(f"{len(failed_actions)} actions failed")
        if failed_tests:
            answer_parts.append(f"{len(failed_tests)} tests failed")
        
        answer = "Build failures: " + ", ".join(answer_parts)
        
        # Create nodes for failed items
        nodes = []
        for target in failed_targets[:10]:  # Limit to first 10
            nodes.append({
                "id": target,
                "label": target.split("/")[-1],
                "type": "target",
                "status": "failed"
            })
        
        return ChatResponse(
            answer=answer,
            graph_nodes=nodes,
            metadata={"failed_targets": failed_targets, "failed_tests": failed_tests}
        )
    
    def _handle_tests(self, question: str) -> ChatResponse:
        """Handle test-related queries"""
        total_tests = len(self.bep_parser.test_results)
        passed_tests = sum(1 for test in self.bep_parser.test_results.values() 
                          if test.get('passed', False))
        failed_tests = total_tests - passed_tests
        
        if total_tests == 0:
            return ChatResponse(answer="No test results found in build data")
        
        answer = f"Test Results: {passed_tests} passed, {failed_tests} failed out of {total_tests} total"
        
        # Create nodes for test results
        nodes = []
        for test_name, test_data in self.bep_parser.test_results.items():
            nodes.append({
                "id": test_name,
                "label": test_name.split("/")[-1],
                "type": "test",
                "status": "success" if test_data.get('passed', False) else "failed"
            })
        
        return ChatResponse(
            answer=answer,
            graph_nodes=nodes,
            metadata={"test_summary": {"total": total_tests, "passed": passed_tests, "failed": failed_tests}}
        )
    
    def _handle_cache(self, question: str) -> ChatResponse:
        """Handle cache-related queries"""
        cache_hits = sum(1 for action in self.bep_parser.actions.values() 
                        if action.get('cache_result') == 'hit')
        cache_misses = sum(1 for action in self.bep_parser.actions.values() 
                          if action.get('cache_result') == 'miss')
        
        total_actions = len(self.bep_parser.actions)
        if total_actions == 0:
            return ChatResponse(answer="No action execution data found")
        
        cache_hit_rate = (cache_hits / total_actions) * 100 if total_actions > 0 else 0
        
        answer = f"Cache Performance: {cache_hits} hits, {cache_misses} misses ({cache_hit_rate:.1f}% hit rate)"
        
        return ChatResponse(
            answer=answer,
            metadata={"cache_stats": {"hits": cache_hits, "misses": cache_misses, "hit_rate": cache_hit_rate}}
        )
    
    def _handle_performance(self, question: str) -> ChatResponse:
        """Handle performance-related queries"""
        if not self.bep_parser.actions:
            return ChatResponse(answer="No performance data available")
        
        execution_times = [action.get('execution_time', 0) for action in self.bep_parser.actions.values()]
        total_time = sum(execution_times)
        max_time = max(execution_times) if execution_times else 0
        avg_time = total_time / len(execution_times) if execution_times else 0
        
        answer = f"Build Performance: Total execution time {total_time:.2f}s, Average {avg_time:.2f}s, Slowest action {max_time:.2f}s"
        
        return ChatResponse(
            answer=answer,
            metadata={"performance": {"total_time": total_time, "avg_time": avg_time, "max_time": max_time}}
        )
    
    def _handle_targets(self, question: str) -> ChatResponse:
        """Handle target-related queries"""
        total_targets = len(self.bep_parser.targets)
        successful_targets = sum(1 for target in self.bep_parser.targets.values() 
                               if target.status == 'success')
        
        answer = f"Build Targets: {successful_targets}/{total_targets} succeeded"
        
        nodes = []
        for target_name, target in list(self.bep_parser.targets.items())[:20]:  # Limit to first 20
            nodes.append({
                "id": target_name,
                "label": target_name.split("/")[-1],
                "type": "target",
                "status": target.status
            })
        
        return ChatResponse(
            answer=answer,
            graph_nodes=nodes
        )
    
    def _handle_summary(self, question: str) -> ChatResponse:
        """Handle summary/overview queries"""
        total_targets = len(self.bep_parser.targets)
        successful_targets = sum(1 for target in self.bep_parser.targets.values() 
                               if target.status == 'success')
        total_tests = len(self.bep_parser.test_results)
        passed_tests = sum(1 for test in self.bep_parser.test_results.values() 
                          if test.get('passed', False))
        
        summary_parts = [
            f"Targets: {successful_targets}/{total_targets} succeeded",
        ]
        
        if total_tests > 0:
            summary_parts.append(f"Tests: {passed_tests}/{total_tests} passed")
        
        if self.bep_parser.actions:
            cache_hits = sum(1 for action in self.bep_parser.actions.values() 
                            if action.get('cache_result') == 'hit')
            total_actions = len(self.bep_parser.actions)
            cache_rate = (cache_hits / total_actions) * 100 if total_actions > 0 else 0
            summary_parts.append(f"Cache hit rate: {cache_rate:.1f}%")
        
        answer = "Build Summary: " + ", ".join(summary_parts)
        
        return ChatResponse(
            answer=answer,
            metadata={
                "summary": {
                    "targets": {"total": total_targets, "successful": successful_targets},
                    "tests": {"total": total_tests, "passed": passed_tests} if total_tests > 0 else None,
                    "actions": len(self.bep_parser.actions)
                }
            }
        )

# Global instances
bep_parser = BEPParser()
chat_engine = ChatEngine(bep_parser)
app = FastAPI(title="Bazel ChatViz API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Bazel ChatViz API is running"}

@app.get("/api/resource-usage")
async def get_resource_usage():
    """Get resource usage data from BEP"""
    resource_data = {
        "cpu": [],
        "memory": [],
        "time": []
    }

    for event in bep_parser.events:
        if "progress" in event:
            timestamp = event.get("timeMillis", 0)
            resource_data["time"].append(timestamp)

            # Extract CPU and memory usage if available
            if "resourceUsage" in event:
                cpu = event["resourceUsage"].get("cpuUsage", 0)
                memory = event["resourceUsage"].get("memoryUsage", 0)
                resource_data["cpu"].append(cpu)
                resource_data["memory"].append(memory)
                
    return resource_data


@app.post("/api/load-bep")
async def load_bep(file: UploadFile = File(...)):
    """Load BEP JSON file"""
    try:
        content = await file.read()
        
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Parse the BEP file
        global bep_parser, chat_engine
        bep_parser = BEPParser()
        bep_parser.parse_file(temp_path)
        chat_engine = ChatEngine(bep_parser)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        return {
            "message": "BEP file loaded successfully",
            "stats": {
                "targets": len(bep_parser.targets),
                "actions": len(bep_parser.actions),
                "tests": len(bep_parser.test_results)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load BEP file: {str(e)}")

@app.get("/api/graph")
async def get_graph():
    """Get dependency graph data"""
    nodes = []
    edges = []
    
    # Convert targets to graph nodes with improved attributes
    for target_name, target in bep_parser.targets.items():
        node_id = target_name.replace('/', '_').replace(':', '_')  # Sanitize ID
        nodes.append({
            "id": node_id,
            "originalId": target_name,
            "label": target_name.split("/")[-1],
            "type": "target",
            "status": target.status,
            "group": target_name.split("/")[1] if len(target_name.split("/")) > 1 else "root"
        })
        
        # Add dependency edges
        if hasattr(target, 'dependencies') and target.dependencies:
            for dep in target.dependencies:
                dep_id = dep.replace('/', '_').replace(':', '_')
                edges.append({
                    "id": f"{node_id}-{dep_id}",
                    "source": node_id,
                    "target": dep_id,
                    "type": "dependency"
                })
    
    # Add test nodes with connections to their targets
    for test_name, test_data in bep_parser.test_results.items():
        node_id = test_name.replace('/', '_').replace(':', '_')
        nodes.append({
            "id": node_id,
            "originalId": test_name,
            "label": test_name.split("/")[-1],
            "type": "test",
            "status": "passed" if test_data.get('passed', False) else "failed",
            "group": test_name.split("/")[1] if len(test_name.split("/")) > 1 else "tests"
        })
        
        # Connect test to its target
        target_id = test_name.replace('/', '_').replace(':', '_').replace('_test', '')
        edges.append({
            "id": f"{node_id}-{target_id}",
            "source": node_id,
            "target": target_id,
            "type": "test"
        })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "totalTargets": len(bep_parser.targets),
            "totalTests": len(bep_parser.test_results),
            "groups": list(set(node["group"] for node in nodes))
        }
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Handle chat queries"""
    try:
        response = chat_engine.query(request.question)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat query failed: {str(e)}")

@app.get("/api/tests")
async def get_tests():
    """Get test results"""
    tests = []
    for test_name, test_data in bep_parser.test_results.items():
        tests.append({
            "name": test_name,
            "status": "passed" if test_data.get('passed', False) else "failed",
            "execution_time": test_data.get('execution_time', 0)
        })
    
    return {"tests": tests}

@app.get("/api/stats")
async def get_stats():
    """Get build statistics"""
    return {
        "targets": len(bep_parser.targets),
        "actions": len(bep_parser.actions),
        "tests": len(bep_parser.test_results),
        "successful_targets": sum(1 for t in bep_parser.targets.values() if t.status == 'success'),
        "passed_tests": sum(1 for t in bep_parser.test_results.values() if t.get('passed', False))
    }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bazel ChatViz Backend Server")
    parser.add_argument("--bep-file", type=str, help="BEP JSON file to load")
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind server to")
    
    args = parser.parse_args()
    
    # Load BEP file if provided
    if args.bep_file:
        if os.path.exists(args.bep_file):
            print(f"Loading BEP file: {args.bep_file}")
            bep_parser.parse_file(args.bep_file)
            global chat_engine
            chat_engine = ChatEngine(bep_parser)
            print(f"Loaded {len(bep_parser.targets)} targets, {len(bep_parser.actions)} actions, {len(bep_parser.test_results)} tests")
        else:
            print(f"Warning: BEP file not found: {args.bep_file}")
    
    print(f"Starting Bazel ChatViz server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()