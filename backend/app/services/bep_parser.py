from typing import Iterable, Dict
import json


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
        