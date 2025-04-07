from dataclasses import dataclass
from typing import Optional, Dict
import time

@dataclass
class StreamPriority:
    """
    Pure application-level stream priority implementation
    """
    weight: int = 256          # Relative priority weight (higher = more important)
    last_sent: float = 0       # Timestamp of last send
    no_of_sends: int = 0        # Total bytes sent
    dependent_on: Optional[int] = None  # Not used in basic implementation
    exclusive: bool = False    # Not used in basic implementation

class PriorityManager:
    """
    Manages stream priorities with application-level scheduling
    """
    def __init__(self):
        self._streams: Dict[int, StreamPriority] = {}
        
    def add_stream(self, stream_id: int, weight: int = 256):
        """Register a new stream with priority weight"""
        self._streams[stream_id] = StreamPriority(weight=weight)
        
    def update_after_send(self, stream_id: int):
        """Update tracking after data is sent"""
        if stream_id in self._streams:
            self._streams[stream_id].last_sent = time.time()
            self._streams[stream_id].no_of_sends += 1
            #print(f"Stream {stream_id} total sent: {self._streams[stream_id].bytes_sent}")
            
    def get_next_stream(self, ready_streams: list[int]) -> Optional[int]:
        """
        Determine which stream should send next using Weighted Fair Queueing (WFQ)
        """
        t = time.time()
        if not ready_streams:
            return None
            
        # Calculate which stream is most "behind" its fair share
        min_score = float('inf')
        selected_stream = ready_streams[0]
        current_time = time.time()
        for stream_id in ready_streams:
            if stream_id not in self._streams:
                continue
                
            priority = self._streams[stream_id]
            # Calculate how much this stream "deserves" to have sent
            deserved_sends = priority.weight * (current_time - priority.last_sent)
            # Score is actual bytes sent minus deserved bytes (lower is better)
            score = priority.no_of_sends - deserved_sends
            
            if score < min_score:
                min_score = score
                selected_stream = stream_id
        print('time taken for picking'  , time.time() - t)
        return selected_stream