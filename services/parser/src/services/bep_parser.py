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

@dataclass
class Target:
    label: str
    status: str = "unknown"           # "unknown" | "success" | "failure"
    kind: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)

class BEPParser:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

        self.targets: Dict[str, Target] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.action_count: int = 0

        self.resource_series: List[Dict[str, Optional[float]]] = []
        # self.rag_processor = BEPRAGProcessor()


    def parse_stream(self, lines: Iterable[str]) -> None:
        self.reset()

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            self.events.append(event)
            try:
                self.process_event(event)
            except Exception:
                continue

    def process_event(self, event: Dict[str, Any]) -> None:
        # check if event id is a dictionary. If not, we cannot reliable process as of now.
        event_id = event.get("id", {})
        if not isinstance(event_id, dict):
            return
        
        # Checking for known id keys and route appropriately
        if "targetCompleted" in event_id:
            self.handle_target_completed(event, event_id["targetCompleted"])
        elif "configuredTarget" in event_id or "targetConfigured" in event_id:
            configured = event_id.get("configuredTarget") or event_id.get("targetConfigured")
            self.handle_target_configured(event, configured)
        elif "actionCompleted" in event_id or "actionExecuted" in event_id:
            self.handle_action(event)
        elif "testResult" in event_id:
            self.handle_test_result(event, event_id["testResult"])
        elif "progress" in event_id:
            self.handle_progress(event)
        elif "buildMetrics" in event:
            self.handle_build_metrics(event)

        self.maybe_extract_resource_point(event)


    def handle_target_completed(self, event: Dict[str, Any], id_payload: Dict[str, Any]) -> None:
        label = id_payload.get("label")
        if not label:
            return
        details = event.get("completed", {}) or event.get("targetCompleted", {}) or {}
        success = bool(details.get("success", False))
        t = self.targets.get(label)  or Target(label=label)
        t.status = "success" if success else "failure"
        self.targets[label] = t


    def handle_target_configured(self, event: Dict[str, Any], id_payload: Dict[str, Any]) -> None:
        label = id_payload.get("label")
        if not label:
            return
        
        t = self.targets.get(label) or Target(label = label)

        configured_payload = event.get("targetKind") or configured_payload.get("kind")
        kind = configured_payload.get("targetKind") or configured_payload.get("kind")
        if kind:
            t.kind = kind

        deps = set()

        for key in ("deps", "dependencies"):
            value = configured_payload.get(key)
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, dict) and "label" in v:
                        deps.add(v["label"])
        
        if deps:
            t.dependencies.update(deps)

        self.targets[label] = t


    def handle_action(self, event: Dict[str, Any]) -> None:
        self.action_count += 1

    
    def handle_test_result(self, event: Dict[str, Any], id_payload: Dict[str, Any]) -> None:
        label = id_payload.get("label")
        if not label:
            return
        
        payload = event.get("testResult", {})
        status = (payload.get("status") or "").lower()
        passed = status in ("passed", "pass", "success", "ok")

        self.test_result[label] = {
            "status": status,
            "passed": passed,
            "run": payload.get("run", 0),
            "attempt": payload.get("attempt", 0),
        }

        t = self.targets.get(label) or Target(label=label)
        if t.status == "unknown":
            t.status = "success" if passed else "failure"
        self.targets[label] = t

    
    def handle_progress(self, event: Dict[str, Any]) -> None:
        # perform no direct action for the progress since our maybe_extract_resource_point handles
        # progress and metrics
        return
    
    def handle_build_metrics(self, event: Dict[str, Any]) -> None:
        # Same as handle_progress, we skip this and let such be handled by maybe_extract_resource_point
        return
    

    def maybe_extract_resource_point(self, event: Dict[str, Any]) -> None:
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
    
    def export_resource_usage(self) -> bytes:
        times: List[Optional[float]] = []
        cpu: List[Optional[float]] = []
        mem: List[Optional[float]] = []

        for point in self.resource_series:
            times.append(point.get("time"))
            cpu.append(point.get("cpu"))
            mem.append(point.get("memory"))

        payload = {
            "time": times,
            "cpu" : cpu,
            "memory": mem,
            "count": len(times),
        }

        return json.dumps(payload).encode("utf-8")
    
    # Dependency graph
    def export_graph(self) -> bytes:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # replace the "/" and ":" with "_" that can be problematic for some graph visualization libraries.
        def safe_id(s: str) -> str:
            return s.replace("/", "_").replace(":", "_")
        
        # Target nodes
        for label, target in self.targets.items():
            gid_parts = label.split("/")
            group = gid_parts[1] if len(gid_parts) > 1 else "root"

            nodes.append({
                "id": safe_id(label),
                "originalId": label,
                "label": label.split("/")[-1],
                "type": "target",
                "status": target.status,
                "kind": target.kind,
                "group": group,
            })

            for dep in sorted(target.dependencies):
                edges.append({
                    "id": f"{safe_id(label)}-{safe_id(dep)}",
                    "source": safe_id(dep),
                    "target": safe_id(label),
                    "type": "dependency",
                })
        
        for test_label, test_data in self.test_results.items():
            nodes.append({
                "id": safe_id(test_label) + "__test",
                "originalId": test_label,
                "label": test_label.split("/")[-1],
                "type": "test",
                "status": "passed" if test_data.get("passed") else "failed",
                "group": "tests",
            })

            edges.append({
                "id": f"{safe_id(test_label)}__test->{safe_id(test_label)}",
                "source": safe_id(test_label) + "__test",
                "target": safe_id(test_label),
                "type": "test",
            })
        
        payload = {
            "nodes":  nodes,
            "edges": edges,
            "metadata": {
                "totalTargets": len(self.targets),
                "totalTests": len(self.test_results),
                "actionSeen": self.action_count,
                "groups": sorted({n["group"] for n in nodes}),
            }
        }

        return json.dumps(payload).encode("utf-8")


    def export_summary(self) -> bytes:
        payload = {
            "targets": len(self.targets),
            "tests": len(self.test_results),
            "actions": self.action_count,
            "has_resource_usage": len(self.resource_series) > 0,
        }
        return json.dumps(payload).encode("utf-8")