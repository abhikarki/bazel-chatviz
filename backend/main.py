import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv


#load environment variables for API keys
load_dotenv()


class BEPRAGProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embeddings = OpenAIEmbeddings(
            openai_api_key = os.getenv("OPENAI_API_KEY"),
            model = "text-embedding-ada-002"
        )
        self.vector_store = None
        self.qa_chain = None
        self.memory = ConversationBufferMemory(
            memory_key = 'chat_history',
            return_messages=True
        )
    
    def process_bep_data(self, bep_events: List[Dict[str, Any]]) -> None:
        """Process BEP data into searchable chunks"""
        # convert events to text
        texts = []
        for event in bep_events:
            # Convert each event to a structured text representation
            text = f"Event Type: {list(event.get('id', {}).keys())[0] if event.get('id') else 'unknown'}\n"
            text += json.dumps(event, indent=2)
            texts.append(text)

        #create chunks
        chunks = self.text_splitter.create_documents(texts)

        #create vector store
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)

        # Initialize QA chain
        llm = ChatOpenAI(temperature = 0)
        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm = llm,
            retriever = self.vector_store.as_retriever(),
            memory=self.memory
        )

    def query(self, question: str) -> str:
        """Query the BEP data using RAG"""
        if not self.qa_chain:
            raise ValueError("BEP data not processed yet")
        
        result = self.qa_chain({"question": question})
        return result['answer']
    



# =========
# Data types
# =========

@dataclass
class Target:
    label: str
    status: str = "unknown"           # "unknown" | "success" | "failure"
    kind: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)


# ======================
# BEP parser (defensive)
# ======================

class BEPParser:
    """
    Minimal, robust BEP parser for:
      - Resource-usage time series (best-effort)
      - Dependency graph (best-effort from configured events)
      - Target completion status
      - Test results

    Design notes:
      • Bazel BEP events are JSON objects, one per line.
      • The event *type* is indicated by keys under event["id"] (e.g., "targetCompleted", "progress", "testResult", "configuredTarget", etc).
      • The detailed payload typically lives in a sibling field (e.g., "completed", "progress", "testResult", "configured", "buildMetrics", ...).
      • Different Bazel versions may vary; we code defensively and ignore what we don’t recognize.
    """

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

        # Graph/targets/tests/action counts
        self.targets: Dict[str, Target] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.action_count: int = 0

        # Resource series (best effort)
        # time: milliseconds (if available); cpu/memory: numeric (unit depends on Bazel version)
        self.resource_series: List[Dict[str, Optional[float]]] = []
        self.rag_processor = BEPRAGProcessor()

    # --------- Public API ---------

    def reset(self) -> None:
        self.__init__()

    def parse_file(self, bep_file_path: str) -> None:
        if not os.path.exists(bep_file_path):
            raise FileNotFoundError(f"BEP file not found: {bep_file_path}")

        self.reset()
        with open(bep_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # Skip bad lines but don’t crash the whole parse
                    continue
                self.events.append(event)
                self._process_event(event)
        
        self.rag_processor.process_bep_data(self.events)

    # --------- Internals ---------

    def _process_event(self, event: Dict[str, Any]) -> None:
        # Determine event kind by looking inside event["id"]
        event_id = event.get("id", {})
        if not isinstance(event_id, dict):
            return

        # We’ll check for known id keys and route accordingly.
        if "targetCompleted" in event_id:
            self._handle_target_completed(event, event_id["targetCompleted"])
        elif "configuredTarget" in event_id or "targetConfigured" in event_id:
            # Some Bazel versions use "configuredTarget", others "targetConfigured".
            configured = event_id.get("configuredTarget") or event_id.get("targetConfigured")
            self._handle_target_configured(event, configured)
        elif "actionCompleted" in event_id or "actionExecuted" in event_id:
            self._handle_action(event)
        elif "testResult" in event_id:
            self._handle_test_result(event, event_id["testResult"])
        elif "progress" in event_id:
            self._handle_progress(event)
        elif "buildMetrics" in event:
            # Sometimes buildMetrics arrive with a generic id; still try to extract.
            self._handle_build_metrics(event)

        # Try resource extraction on any event (no-op if nothing present).
        self._maybe_extract_resource_point(event)

    # ---- handlers ----

    def _handle_target_completed(self, event: Dict[str, Any], id_payload: Dict[str, Any]) -> None:
        label = id_payload.get("label")
        if not label:
            return
        # The details are commonly in event["completed"] with "success": true/false
        details = event.get("completed", {}) or event.get("targetCompleted", {}) or {}
        success = bool(details.get("success", False))
        t = self.targets.get(label) or Target(label=label)
        t.status = "success" if success else "failure"
        # keep kind/deps if already recorded earlier
        self.targets[label] = t

    def _handle_target_configured(self, event: Dict[str, Any], id_payload: Dict[str, Any]) -> None:
        """
        Try to pull:
          - label (string)
          - kind (string)
          - dependencies (list of labels) if present under a "configured" payload
        """
        label = id_payload.get("label")
        if not label:
            return

        t = self.targets.get(label) or Target(label=label)

        # Commonly found in event["configured"], but we’ll also probe event["targetConfigured"]
        configured_payload = event.get("configured") or event.get("targetConfigured") or {}
        # target kind
        kind = configured_payload.get("targetKind") or configured_payload.get("kind")
        if kind:
            t.kind = kind

        # Dependencies are not always included in BEP; if present, they might live as a list of labels
        # under fields like "deps", "dependencies", or nested structures. We’ll be permissive:
        # Example shapes we’ll accept:
        #   {"configured": {"deps": ["//pkg:dep1","//pkg:dep2"]}}
        #   {"configured": {"dependencies": [{"label":"//pkg:dep"}]}}
        deps = set()

        # Case 1: simple list of strings
        for key in ("deps", "dependencies"):
            value = configured_payload.get(key)
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, str):
                        deps.add(v)
                    elif isinstance(v, dict) and "label" in v:
                        deps.add(v["label"])

        # Assign if found
        if deps:
            t.dependencies.update(deps)

        self.targets[label] = t

    def _handle_action(self, event: Dict[str, Any]) -> None:
        # We don’t build a full action graph here; just count them
        self.action_count += 1

    def _handle_test_result(self, event: Dict[str, Any], id_payload: Dict[str, Any]) -> None:
        """
        testResult id payload usually contains the target label for the test.
        The detailed payload is usually in event["testResult"] with status.
        """
        label = id_payload.get("label")
        if not label:
            return

        payload = event.get("testResult", {})
        # Many BEP variants use "status": "PASSED"|"FAILED"|"FLAKY"|...
        status = (payload.get("status") or "").lower()
        passed = status in ("passed", "pass", "success", "ok")

        self.test_results[label] = {
            "status": status,
            "passed": passed,
            "run": payload.get("run", 0),
            "attempt": payload.get("attempt", 0),
        }

        # Optionally reflect result onto the target
        t = self.targets.get(label) or Target(label=label)
        if t.status == "unknown":
            t.status = "success" if passed else "failure"
        self.targets[label] = t

    def _handle_progress(self, event: Dict[str, Any]) -> None:
        # Some Bazel versions may stuff resource hints in a "progress" payload.
        # We don’t need to do anything special here beyond letting _maybe_extract_resource_point run.
        return

    def _handle_build_metrics(self, event: Dict[str, Any]) -> None:
        # Metrics sometimes appear here (e.g., memory), but extraction is centralized below.
        return

    # ---- resource extraction (best-effort, tolerant) ----

    def _maybe_extract_resource_point(self, event: Dict[str, Any]) -> None:
        """
        Bazel’s BEP does not have a single canonical resource-usage schema across all versions.
        We attempt multiple plausible places/keys and store whatever we find:

          time_ms: event.get("timeMillis") | event.get("timestamp") | None
          cpu:  event["progress"]["resourceUsage"]["cpuUsage"] | event["buildMetrics"]["timingMetrics"]["cpu"] | ...
          mem:  event["progress"]["resourceUsage"]["memoryUsage"] | event["buildMetrics"]["memoryMetrics"]["peak"] | ...

        If none are found, we skip the point.
        """
        get_num = lambda x: float(x) if isinstance(x, (int, float)) else None

        # Timestamp: prefer timeMillis, then timestamp
        time_ms = event.get("timeMillis")
        if not isinstance(time_ms, (int, float)):
            time_ms = event.get("timestamp")
        time_ms = get_num(time_ms)

        # Try a few likely nests for CPU/memory
        cpu = None
        mem = None

        # progress.resourceUsage.{cpuUsage, memoryUsage}
        progress = event.get("progress")
        if isinstance(progress, dict):
            ru = progress.get("resourceUsage")
            if isinstance(ru, dict):
                cpu = cpu or get_num(ru.get("cpuUsage") or ru.get("cpu") or ru.get("cpu_utilization"))
                mem = mem or get_num(ru.get("memoryUsage") or ru.get("memory") or ru.get("mem"))

        # buildMetrics.memoryMetrics.{peak, highWatermark, used}
        bm = event.get("buildMetrics")
        if isinstance(bm, dict):
            mem_metrics = bm.get("memoryMetrics")
            if isinstance(mem_metrics, dict):
                mem = mem or get_num(
                    mem_metrics.get("peak")
                    or mem_metrics.get("highWatermark")
                    or mem_metrics.get("used")
                )
            # timingMetrics might have CPU-ish hints (rare)
            timing = bm.get("timingMetrics")
            if isinstance(timing, dict):
                cpu = cpu or get_num(
                    timing.get("cpu") or timing.get("utilization") or timing.get("processTimeMs")
                )
                # If timing gives process time in ms and no timestamp, we still record.

        # If we found anything meaningful, store it
        if time_ms is not None or cpu is not None or mem is not None:
            self.resource_series.append(
                {
                    "time": time_ms,
                    "cpu": cpu,
                    "memory": mem,
                }
            )


# =========
# Web server
# =========

bep_parser = BEPParser()
app = FastAPI(title="Bazel BEP Viz API", version="1.0.0")

# CORS: allow local dev frontends by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",  # loosen for local experiments; tighten for prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Bazel BEP Viz API is running"}


@app.get("/api/resource-usage")
async def get_resource_usage():
    """
    Returns a simple time series for resource usage. Because BEP formats vary,
    any of time/cpu/memory can be None if Bazel didn't emit them.
    """
    # Already pre-extracted during parse; just return.
    # To make it frontend-friendly, split into parallel arrays:
    times: List[Optional[float]] = []
    cpu: List[Optional[float]] = []
    mem: List[Optional[float]] = []

    for point in bep_parser.resource_series:
        times += [point.get("time")]
        cpu += [point.get("cpu")]
        mem += [point.get("memory")]

    return {
        "time": times,
        "cpu": cpu,
        "memory": mem,
        "count": len(times),
    }


@app.get("/api/graph")
async def get_graph():
    """
    Dependency graph from best-effort BEP parsing:
      nodes: targets + tests
      edges: target dependency edges + test->target edges
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Helper to make DOM-safe IDs
    def safe_id(s: str) -> str:
        return s.replace("/", "_").replace(":", "_")

    # Target nodes
    for label, target in bep_parser.targets.items():
        gid_parts = label.split("/")
        group = gid_parts[1] if len(gid_parts) > 1 else "root"

        nodes.append(
            {
                "id": safe_id(label),
                "originalId": label,
                "label": label.split("/")[-1],
                "type": "target",
                "status": target.status,
                "kind": target.kind,
                "group": group,
            }
        )

        # Dependencies
        for dep in sorted(target.dependencies):
            edges.append(
                {
                    "id": f"{safe_id(label)}-{safe_id(dep)}",
                    "source": safe_id(label),
                    "target": safe_id(dep),
                    "type": "dependency",
                }
            )

    # Test nodes and edges to their target (same label)
    for test_label, test_data in bep_parser.test_results.items():
        nodes.append(
            {
                "id": safe_id(test_label) + "__test",
                "originalId": test_label,
                "label": test_label.split("/")[-1],
                "type": "test",
                "status": "passed" if test_data.get("passed") else "failed",
                "group": "tests",
            }
        )
        # Connect test node to its corresponding target node (same label)
        edges.append(
            {
                "id": f"{safe_id(test_label)}__test->{safe_id(test_label)}",
                "source": safe_id(test_label) + "__test",
                "target": safe_id(test_label),
                "type": "test",
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "totalTargets": len(bep_parser.targets),
            "totalTests": len(bep_parser.test_results),
            "actionsSeen": bep_parser.action_count,
            "groups": sorted({n["group"] for n in nodes}),
        },
    }


class QueryRequest(BaseModel):
    query: str

# API endpoint for querying
@app.post("/api/query")
async def query_bep(request: QueryRequest):
    """Query the BEP data using RAG"""
    try:
        if not bep_parser.rag_processor.vector_store:
            raise HTTPException(
                status_code=400,
                detail="No BEP data processed for RAG"
            )

        response = bep_parser.rag_processor.query(request.query)
        return{
            "query": request.query,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bazel BEP Visualization Backend")
    parser.add_argument("--bep-file", type=str, help="Path to BEP JSONL file")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host")
    args = parser.parse_args()

    if args.bep_file:
        path = Path(args.bep_file)
        if path.exists():
            print(f"[BEP] Loading: {path}")
            bep_parser.parse_file(str(path))
            print(
                f"[BEP] Loaded {len(bep_parser.targets)} targets, "
                f"{bep_parser.action_count} actions, "
                f"{len(bep_parser.test_results)} tests, "
                f"{len(bep_parser.resource_series)} resource points"
            )
        else:
            print(f"[WARN] BEP file not found: {path}")

    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
