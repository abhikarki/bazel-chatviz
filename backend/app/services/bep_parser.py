from typing import Iterable

class BEPParser:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

        self.targets: Dict[str, Target] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.action_count: int = 0

        self.resource_series: List[Dict[str, Optional[float]]] = []
        self.rag_processor = BEPRAGProcessor()


    
