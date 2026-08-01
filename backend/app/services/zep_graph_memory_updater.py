"""
Zep Map memory update service
Simulate the Agent Activity updates to Zep in the map
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_locale, set_locale
from ..utils.zep import (
    ZEP_INGESTION_WAIT_TIMEOUT_SECONDS,
    call_zep_read_with_retry,
    get_zep_client,
)

logger = get_logger('mirofish.zep_graph_memory_updater')


@dataclass
class AgentActivity:
    """Agent activity record"""
    platform: str           # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str        # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str

    def to_episode_text(self) -> str:
        """
        Convert the activity to something that can be sent to Zep text description of

        Use natural language description format,let Zep Ability to extract entities and relationships from
        Do not add simulation related prefixes,Avoid misleading map updates
        """
        # Generate different descriptions based on different action types
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }

        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()

        # Keep the event time in the source text as well as episode metadata so
        # temporal extraction does not collapse a multi-action batch.
        return (
            f"[{self.timestamp}] [{self.platform} round {self.round_num}] "
            f"{self.agent_name}: {description}"
        )

    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"posted a post:[{content}]"
        return "posted a post"

    def _describe_like_post(self) -> str:
        """Like the post - Contains the original text of the post and author information"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")

        if post_content and post_author:
            return f"Liked{post_author}s posts:[{post_content}]"
        elif post_content:
            return f"Liked a post:[{post_content}]"
        elif post_author:
            return f"Liked{post_author}a post of"
        return "Liked a post"

    def _describe_dislike_post(self) -> str:
        """Dislike the post - Contains the original text of the post and author information"""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")

        if post_content and post_author:
            return f"stepped on{post_author}s posts:[{post_content}]"
        elif post_content:
            return f"Disliked a post:[{post_content}]"
        elif post_author:
            return f"stepped on{post_author}a post of"
        return "Disliked a post"

    def _describe_repost(self) -> str:
        """Retweet post - Contains original post content and author information"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")

        if original_content and original_author:
            return f"Forwarded{original_author}s posts:[{original_content}]"
        elif original_content:
            return f"retweeted a post:[{original_content}]"
        elif original_author:
            return f"Forwarded{original_author}a post of"
        return "retweeted a post"

    def _describe_quote_post(self) -> str:
        """quote post - Contains original post content,Author information and citation comments"""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")

        base = ""
        if original_content and original_author:
            base = f"quoted{original_author}s posts[{original_content}]"
        elif original_content:
            base = f"quoted a post[{original_content}]"
        elif original_author:
            base = f"quoted{original_author}a post of"
        else:
            base = "quoted a post"

        if quote_content:
            base += f",and commented:[{quote_content}]"
        return base

    def _describe_follow(self) -> str:
        """Follow users - Contains the name of the followed user"""
        target_user_name = self.action_args.get("target_user_name", "")

        if target_user_name:
            return f"Followed users[{target_user_name}]"
        return "Followed a user"

    def _describe_create_comment(self) -> str:
        """Leave a comment - Contains comment content and information about the post being commented on"""
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")

        if content:
            if post_content and post_author:
                return f"in{post_author}s posts[{post_content}]Commented below:[{content}]"
            elif post_content:
                return f"in post[{post_content}]Commented below:[{content}]"
            elif post_author:
                return f"in{post_author}commented on the post:[{content}]"
            return f"commented:[{content}]"
        return "Posted a comment"

    def _describe_like_comment(self) -> str:
        """Like and comment - Contains review content and author information"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")

        if comment_content and comment_author:
            return f"Liked{comment_author}comments:[{comment_content}]"
        elif comment_content:
            return f"Liked a comment:[{comment_content}]"
        elif comment_author:
            return f"Liked{comment_author}a comment of"
        return "Liked a comment"

    def _describe_dislike_comment(self) -> str:
        """Dislike comments - Contains review content and author information"""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")

        if comment_content and comment_author:
            return f"stepped on{comment_author}comments:[{comment_content}]"
        elif comment_content:
            return f"Disliked a comment:[{comment_content}]"
        elif comment_author:
            return f"stepped on{comment_author}a comment of"
        return "Disliked a comment"

    def _describe_search(self) -> str:
        """Search posts - Contains search keywords"""
        query = self.action_args.get("query", "") or self.action_args.get("keyword", "")
        return f"Searched[{query}]" if query else "Searched"

    def _describe_search_user(self) -> str:
        """Search users - Contains search keywords"""
        query = self.action_args.get("query", "") or self.action_args.get("username", "")
        return f"Searched for users[{query}]" if query else "Searched for users"

    def _describe_mute(self) -> str:
        """Block user - Contains the name of the blocked user"""
        target_user_name = self.action_args.get("target_user_name", "")

        if target_user_name:
            return f"Blocked user[{target_user_name}]"
        return "Blocked a user"

    def _describe_generic(self) -> str:
        # For unknown action types,Generate a generic description
        return f"Executed{self.action_type}Operation"


class _DrainDeadlineExceeded(TimeoutError):
    def __init__(self, processed_count: int):
        super().__init__("Zep updater drain deadline elapsed")
        self.processed_count = processed_count


class ZepGraphMemoryUpdater:
    """
    Zep Map memory updater

    monitoring simulated actions log file,will new agent Activities are updated in real time to Zep in the map.
    Group by platform,every accumulation BATCH_SIZE Send them in batches after activities Zep.

    All meaningful actions will be updated to Zep,action_args will contain complete contextual information:
    - Like/The original text of the disliked post
    - forward/Quoted original post
    - Follow/Blocked username
    - Like/Comment original text
    """

    # Batch send size(How many items are accumulated on each platform before sending)
    BATCH_SIZE = 5

    # Platform name mapping(for console display)
    PLATFORM_DISPLAY_NAMES = {
        'twitter': 'world 1',
        'reddit': 'world 2',
    }

    # sending interval(seconds),Avoid requesting too quickly
    SEND_INTERVAL = 0.5

    # Zep recommends keeping an episode below 10,000 characters. Leave room
    # for future source formatting changes.
    MAX_EPISODE_CHARS = 9_500

    def __init__(
        self,
        graph_id: str,
        api_key: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ):
        """
        Initialize updater

        Args:
            graph_id: Zep Atlas ID
            api_key: Zep API Key(Optional,Default is read from configuration)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id or "unknown"
        self.api_key = api_key or Config.ZEP_API_KEY

        if not self.api_key:
            raise ValueError("ZEP_API_KEY Not configured")

        self.client = get_zep_client(self.api_key)

        # activity queue
        self._activity_queue: Queue = Queue()

        # Activity buffers grouped by platform(Each platform has accumulated BATCH_SIZE Send in batches)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()
        self._acceptance_lock = threading.Lock()

        # control flag
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Statistics
        self._total_activities = 0  # Number of activities actually added to the queue
        self._total_sent = 0        # Successfully sent to Zep number of batches
        self._total_items_sent = 0  # Successfully sent to Zep number of activities
        self._failed_count = 0      # Number of batches that failed to be sent
        self._skipped_count = 0     # Number of activities skipped by filter(DO_NOTHING)
        self._failed_batches: List[Dict[str, Any]] = []
        self._pending_episode_uuids: List[str] = []

        logger.info(f"ZepGraphMemoryUpdater Initialization completed: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")

    def _get_platform_display_name(self, platform: str) -> str:
        """Get the display name of the platform"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)

    def start(self):
        """Start background worker thread"""
        if self._running:
            return

        # Capture locale before spawning background thread
        current_locale = get_locale()

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(current_locale,),
            daemon=True,
            name=f"ZepMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        logger.info(f"ZepGraphMemoryUpdater Started: graph_id={self.graph_id}")

    def stop(self):
        """Drain the worker, flush tail events, and wait for Cloud ingestion."""
        deadline = time.time() + ZEP_INGESTION_WAIT_TIMEOUT_SECONDS
        # Serialize the accepting->closed transition with add_activity's
        # check+enqueue operation. This closes the small race where a producer
        # could enqueue after both the worker and final flush had exited.
        with self._acceptance_lock:
            self._running = False

        if self._worker_thread and self._worker_thread.is_alive():
            join_timeout = max(0.0, deadline - time.time())
            self._worker_thread.join(timeout=join_timeout)
            if self._worker_thread.is_alive():
                raise TimeoutError(
                    f"Zep updater worker did not stop within {join_timeout:.0f}s"
                )

        # The worker has drained the queue. Only now is it safe to flush
        # buffers; doing this before join loses an item already dequeued by the
        # worker but not yet buffered.
        self._flush_remaining(deadline=deadline)

        if self._failed_batches:
            raise RuntimeError(
                f"{len(self._failed_batches)} Zep activity batch(es) failed; "
                "simulation graph ingestion is incomplete"
            )

        self._wait_for_pending_episodes(deadline=deadline)

        logger.info(f"ZepGraphMemoryUpdater Stopped: graph_id={self.graph_id}, "
                   f"total_activities={self._total_activities}, "
                   f"batches_sent={self._total_sent}, "
                   f"items_sent={self._total_items_sent}, "
                   f"failed={self._failed_count}, "
                   f"skipped={self._skipped_count}")

    def add_activity(self, activity: AgentActivity):
        """
        add a agent Activity to queue

        All meaningful actions will be added to the queue,include:
        - CREATE_POST(post)
        - CREATE_COMMENT(Comment)
        - QUOTE_POST(quote post)
        - SEARCH_POSTS(Search posts)
        - SEARCH_USER(Search users)
        - LIKE_POST/DISLIKE_POST(Like/Dislike the post)
        - REPOST(forward)
        - FOLLOW(Follow)
        - MUTE(shield)
        - LIKE_COMMENT/DISLIKE_COMMENT(Like/Dislike comments)

        action_args will contain complete contextual information(As the original text of the post,Username etc).

        Args:
            activity: Agent activity record
        """
        # skip DO_NOTHING type of activity
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return

        with self._acceptance_lock:
            if not self._running:
                raise RuntimeError("Zep graph updater is not running")
            self._activity_queue.put(activity)
            self._total_activities += 1
        logger.debug(f"Add activity to Zep Queue: {activity.agent_name} - {activity.action_type}")

    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        Add activities from dictionary data

        Args:
            data: from actions.jsonl parsed dictionary data
            platform: Platform name (twitter/reddit)
        """
        # Skip entries for event type
        if "event_type" in data:
            return
        if data.get("success") is False:
            self._skipped_count += 1
            return

        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )

        self.add_activity(activity)

    def _worker_loop(self, locale: str = 'en'):
        """background work loop - Send events in batches by platform to Zep"""
        set_locale(locale)
        while self._running or not self._activity_queue.empty():
            try:
                # Try to get activity from queue(timeout 1 seconds)
                try:
                    activity = self._activity_queue.get(timeout=1)

                    # Add the activity to the buffer for the corresponding platform
                    platform = activity.platform.lower()
                    batch = None
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)

                        # Check if the platform has reached the batch size
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]

                    # Never hold the buffer lock across network I/O or sleep.
                    if batch:
                        self._send_batch_activities(batch, platform)
                        time.sleep(self.SEND_INTERVAL)

                except Empty:
                    pass

            except Exception as e:
                logger.error(f"Abnormal work cycle: {e}")
                time.sleep(1)

    def _build_episode_payloads(
        self,
        activities: List[AgentActivity],
    ) -> List[tuple[List[AgentActivity], str]]:
        payloads: List[tuple[List[AgentActivity], str]] = []
        current_activities: List[AgentActivity] = []
        current_lines: List[str] = []
        current_length = 0

        for activity in activities:
            text = activity.to_episode_text()
            if len(text) > self.MAX_EPISODE_CHARS:
                marker = "... [truncated by MiroFish]"
                text = text[: self.MAX_EPISODE_CHARS - len(marker)] + marker
            projected_length = current_length + (1 if current_lines else 0) + len(text)
            if current_lines and projected_length > self.MAX_EPISODE_CHARS:
                payloads.append((current_activities, "\n".join(current_lines)))
                current_activities = []
                current_lines = []
                current_length = 0
            current_activities.append(activity)
            current_lines.append(text)
            current_length += (1 if len(current_lines) > 1 else 0) + len(text)

        if current_lines:
            payloads.append((current_activities, "\n".join(current_lines)))
        return payloads

    def _send_batch_activities(
        self,
        activities: List[AgentActivity],
        platform: str,
        *,
        deadline: float | None = None,
    ) -> int:
        """
        Send events in bulk to Zep Atlas(merge into one text)

        Args:
            activities: Agent Activity list
            platform: Platform name
        """
        if not activities:
            return 0

        processed_count = 0
        for payload_activities, combined_text in self._build_episode_payloads(activities):
            if deadline is not None and time.time() >= deadline:
                raise _DrainDeadlineExceeded(processed_count)
            try:
                episode = self.client.graph.add(
                    graph_id=self.graph_id,
                    type="text",
                    data=combined_text,
                    created_at=self._to_rfc3339(payload_activities[-1].timestamp),
                    source_description="MiroFish simulation activity batch",
                    metadata={
                        "source": "mirofish_simulation",
                        "simulation_id": self.simulation_id,
                        "platform": platform,
                        "activity_count": len(payload_activities),
                        "first_round": min(a.round_num for a in payload_activities),
                        "last_round": max(a.round_num for a in payload_activities),
                        "agent_ids": ",".join(
                            str(value)
                            for value in sorted({a.agent_id for a in payload_activities})
                        ),
                        "action_types": ",".join(
                            value
                            for value in sorted({a.action_type for a in payload_activities})
                            if value
                        ) or "unknown",
                    },
                )

                episode_uuid = (
                    getattr(episode, "uuid_", None)
                    or getattr(episode, "uuid", None)
                )
                if not episode_uuid:
                    raise RuntimeError("Zep graph.add returned no episode UUID")
                self._pending_episode_uuids.append(str(episode_uuid))
                self._total_sent += 1
                self._total_items_sent += len(payload_activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(f"Successfully sent in batches {len(payload_activities)} Article{display_name}Activity to map {self.graph_id}")
                logger.debug(f"Batch content preview: {combined_text[:200]}...")

            except Exception as e:
                # graph.add has no idempotency key. Replaying an ambiguous
                # response can duplicate extracted facts, so fail closed and
                # surface the incomplete batch to SimulationRunner.
                logger.error(f"Send in bulk to Zep failed,Non-idempotent writes not automatically replayed: {e}")
                self._failed_count += 1
                self._failed_batches.append({
                    "platform": platform,
                    "activities": payload_activities,
                    "error": str(e),
                })
            finally:
                # Successes have a confirmed episode UUID; failures are kept
                # durably in _failed_batches and must never be replayed. Either
                # way this payload is accounted for before moving on.
                processed_count += len(payload_activities)
        return processed_count

    @staticmethod
    def _to_rfc3339(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.isoformat()
        except (AttributeError, TypeError, ValueError):
            return datetime.now().astimezone().isoformat()

    def _flush_remaining(self, *, deadline: float | None = None):
        """Send remaining activity in queue and buffer"""
        # Process the remaining activities in the queue first,add to buffer
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break

        for platform in list(self._platform_buffers):
            with self._buffer_lock:
                buffer = list(self._platform_buffers.get(platform, []))
            if not buffer:
                continue
            display_name = self._get_platform_display_name(platform)
            logger.info(f"send{display_name}The rest of the platform {len(buffer)} Activities")
            if deadline is not None and time.time() >= deadline:
                raise TimeoutError(
                    "Zep updater drain deadline elapsed before flushing all activities"
                )
            try:
                processed_count = self._send_batch_activities(
                    buffer,
                    platform,
                    deadline=deadline,
                )
            except _DrainDeadlineExceeded as error:
                with self._buffer_lock:
                    del self._platform_buffers[platform][:error.processed_count]
                raise TimeoutError(str(error)) from error
            else:
                with self._buffer_lock:
                    del self._platform_buffers[platform][:processed_count]

    def _wait_for_pending_episodes(self, *, deadline: float | None = None) -> None:
        pending = set(self._pending_episode_uuids)
        if not pending:
            return

        if deadline is None:
            deadline = time.time() + ZEP_INGESTION_WAIT_TIMEOUT_SECONDS
        while pending:
            if time.time() >= deadline:
                raise TimeoutError(
                    f"Zep simulation ingestion timed out with {len(pending)} "
                    "episode(s) pending"
                )
            for episode_uuid in list(pending):
                episode = call_zep_read_with_retry(
                    lambda: self.client.graph.episode.get(uuid_=episode_uuid),
                    operation_name=f"poll simulation episode {episode_uuid}",
                )
                if getattr(episode, "processed", False):
                    pending.remove(episode_uuid)
            if pending:
                time.sleep(3)
        self._pending_episode_uuids = []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}

        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,  # The total number of activities added to the queue
            "batches_sent": self._total_sent,            # Number of batches sent successfully
            "items_sent": self._total_items_sent,        # Number of successfully sent events
            "failed_count": self._failed_count,          # Number of batches that failed to be sent
            "pending_episode_count": len(self._pending_episode_uuids),
            "skipped_count": self._skipped_count,        # Number of activities skipped by filter(DO_NOTHING)
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                # Buffer size for each platform
            "running": self._running,
        }


class ZepGraphMemoryManager:
    """
    Manage multiple simulations Zep Map memory updater

    Each simulation can have its own updater instance
    """

    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()

    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        """
        Create a map memory updater for the simulation

        Args:
            simulation_id: Simulation ID
            graph_id: Zep Atlas ID

        Returns:
            ZepGraphMemoryUpdater Example
        """
        with cls._lock:
            # if already exists,Stop the old one first
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()

            updater = ZepGraphMemoryUpdater(
                graph_id,
                simulation_id=simulation_id,
            )
            updater.start()
            cls._updaters[simulation_id] = updater
            cls._stop_all_done = False

            logger.info(f"Create a map memory updater: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater

    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        """Get the simulated updater"""
        with cls._lock:
            return cls._updaters.get(simulation_id)

    @classmethod
    def get_simulation_ids_for_graph(cls, graph_id: str) -> List[str]:
        """Return simulations whose updater still owns or drains this graph."""

        with cls._lock:
            return sorted(
                simulation_id
                for simulation_id, updater in cls._updaters.items()
                if updater.graph_id == graph_id
            )

    @classmethod
    def get_simulation_ids(cls) -> List[str]:
        """Return every simulation with a retained updater."""

        with cls._lock:
            return sorted(cls._updaters)

    @classmethod
    def discard_inactive_updater(cls, simulation_id: str) -> bool:
        """Discard a failed, fully stopped updater during graph destruction."""

        with cls._lock:
            updater = cls._updaters.get(simulation_id)
            if updater is None:
                return False
            worker_alive = bool(
                updater._worker_thread and updater._worker_thread.is_alive()
            )
            if updater._running or worker_alive:
                raise RuntimeError(
                    f"Zep updater for {simulation_id} is still active"
                )
            cls._updaters.pop(simulation_id, None)
        logger.warning(
            "Discarded incomplete Zep updater during explicit graph deletion: "
            "simulation_id=%s, graph_id=%s",
            simulation_id,
            updater.graph_id,
        )
        return True

    @classmethod
    def stop_updater(cls, simulation_id: str):
        """Stop and remove simulated updater"""
        with cls._lock:
            updater = cls._updaters.get(simulation_id)
        if updater is None:
            return

        # Do not hold the manager lock through up to several minutes of Cloud
        # polling. Crucially, only remove the updater after a successful drain;
        # on failure it remains visible to report/deletion barriers and can be
        # stopped again.
        updater.stop()
        with cls._lock:
            if cls._updaters.get(simulation_id) is updater:
                cls._updaters.pop(simulation_id, None)
        logger.info(f"Map memory updater stopped: simulation_id={simulation_id}")

    # prevent stop_all Flag for repeated calls
    _stop_all_done = False

    @classmethod
    def stop_all(cls):
        """Stop all updaters"""
        # Prevent repeated calls
        if cls._stop_all_done:
            return

        with cls._lock:
            simulation_ids = list(cls._updaters)

        errors = []
        for simulation_id in simulation_ids:
            try:
                cls.stop_updater(simulation_id)
            except Exception as error:
                # Keep a failed updater registered so the caller can retry and
                # lifecycle/report guards still see the incomplete ingestion.
                logger.error(
                    "Failed to stop updater: simulation_id=%s, error=%s",
                    simulation_id,
                    error,
                )
                errors.append((simulation_id, error))

        with cls._lock:
            cls._stop_all_done = not cls._updaters

        if errors:
            details = "; ".join(
                f"{simulation_id}: {error}"
                for simulation_id, error in errors
            )
            raise RuntimeError(f"Some map updaters did not stop completely: {details}")
        logger.info("All map memory updaters stopped")

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all updaters"""
        return {
            sim_id: updater.get_stats()
            for sim_id, updater in cls._updaters.items()
        }
