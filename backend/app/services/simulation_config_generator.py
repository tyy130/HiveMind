"""
Simulation configuration smart generator
use LLM According to simulation needs,Document content,Spectral information automatically generates detailed simulation parameters
Realize full automation,No need to manually set parameters

Adopt a step-by-step generation strategy,Avoid failure caused by generating too long content at once:
1. Build time configuration
2. Generate event configuration
3. Batch generation Agent Configuration
4. Generate platform configuration
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, t
from ..utils.openai_chat_compat import create_chat_completion, extract_chat_completion_text
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.simulation_config')

# Illustrative local-time activity schedule used when no audience context exists.
DEFAULT_DAILY_SCHEDULE = {
    # late night(Almost no activity)
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # morning session(gradually wake up)
    "morning_hours": [6, 7, 8],
    # working hours
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # evening peak(most active)
    "peak_hours": [19, 20, 21, 22],
    # Night time period(Decreased activity)
    "night_hours": [23],
    # activity coefficient
    "activity_multipliers": {
        "dead": 0.05,      # Almost no one in the early morning
        "morning": 0.4,    # Become more active in the morning
        "work": 0.7,       # Moderate working hours
        "peak": 1.5,       # evening peak
        "night": 0.5       # late night drop
    }
}


@dataclass
class AgentActivityConfig:
    """single Agent activity configuration"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str

    # Activity configuration (0.0-1.0)
    activity_level: float = 0.5  # Overall activity

    # speaking frequency(Expected number of speeches per hour)
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0

    # Active time period(24 hour clock,0-23)
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))

    # Response speed(Delayed response to hot-button events,unit:Simulation minutes)
    response_delay_min: int = 5
    response_delay_max: int = 60

    # emotional tendencies (-1.0 Arrive 1.0,negative to positive)
    sentiment_bias: float = 0.0

    # stance(attitude towards a particular topic)
    stance: str = "neutral"  # supportive, opposing, neutral, observer

    # influence weight(Deciding to have his or her speech heard by others Agent probability of seeing)
    influence_weight: float = 1.0


@dataclass
class TimeSimulationConfig:
    """Time simulation configuration based on a generic daily activity cycle."""
    # Total simulation time(Simulation hours)
    total_simulation_hours: int = 72  # Default simulation 72 hours(3 day)

    # Rep time per round(Simulation minutes)- Default 60 minutes(1 hours),Speed up the flow of time
    minutes_per_round: int = 60

    # activated every hour Agent Quantity range
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20

    # Evening peak hours in the simulation's inferred local time.
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5

    # Trough period(early morning 0-5 point,Almost no activity)
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  # Very low activity in the early morning

    # morning session
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4

    # working hours
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """event configuration"""
    # initial event(Trigger event when simulation starts)
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)

    # timed event(Events triggered at a specific time)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)

    # hot topic keywords
    hot_topics: List[str] = field(default_factory=list)

    # Public opinion guidance direction
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """Platform specific configuration"""
    platform: str  # twitter or reddit

    # Recommended algorithm weight
    recency_weight: float = 0.4  # time freshness
    popularity_weight: float = 0.3  # Hotness
    relevance_weight: float = 0.3  # Relevance

    # Virus transmission threshold(How many interactions are reached before spreading is triggered)
    viral_threshold: int = 10

    # Echo Chamber Effect Strength(The degree of aggregation of similar opinions)
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """Complete simulation parameter configuration"""
    # Basic information
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str

    # Time configuration
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)

    # Agent Configuration list
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)

    # event configuration
    event_config: EventConfig = field(default_factory=EventConfig)

    # Platform configuration
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None

    # LLM Configuration
    llm_model: str = ""
    llm_base_url: str = ""

    # Generate metadata
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLM explanation of reasoning

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    Simulation configuration smart generator

    use LLM Analyze simulation requirements,Document content,Map entity information,
    Automatically generate optimal simulation parameter configurations

    Adopt a step-by-step generation strategy:
    1. Build time configuration and event configuration(lightweight)
    2. Batch generation Agent Configuration(per batch 10-20 a)
    3. Generate platform configuration
    """

    # Maximum number of characters in context
    MAX_CONTEXT_LENGTH = 50000
    # generated in each batch Agent Quantity
    AGENTS_PER_BATCH = 15

    # Context truncation length for each step(Number of characters)
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # Time configuration
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # event configuration
    ENTITY_SUMMARY_LENGTH = 300          # Entity summary
    AGENT_SUMMARY_LENGTH = 300           # Agent Summary of entities in configuration
    ENTITIES_PER_TYPE_DISPLAY = 20       # Display quantity of each type of entity

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY Not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        Intelligent generation of complete simulation configurations(Step by step generation)

        Args:
            simulation_id: Simulation ID
            project_id: Project ID
            graph_id: Atlas ID
            simulation_requirement: Simulation requirement description
            document_text: Original document content
            entities: Filtered entity list
            enable_twitter: Whether to enable Twitter
            enable_reddit: Whether to enable Reddit
            progress_callback: Progress callback function(current_step, total_steps, message)

        Returns:
            SimulationParameters: Complete simulation parameters
        """
        logger.info(f"Start intelligently generating simulation configurations: simulation_id={simulation_id}, Number of entities={len(entities)}")

        # Calculate the total number of steps
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # Time configuration + event configuration + N batch Agent + Platform configuration
        current_step = 0

        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")

        # 1. Build basic contextual information
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )

        reasoning_parts = []

        # ========== steps 1: Build time configuration ==========
        report_progress(1, t('progress.generatingTimeConfig'))
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"{t('progress.timeConfigLabel')}: {time_config_result.get('reasoning', t('common.success'))}")

        # ========== steps 2: Generate event configuration ==========
        report_progress(2, t('progress.generatingEventConfig'))
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"{t('progress.eventConfigLabel')}: {event_config_result.get('reasoning', t('common.success'))}")

        # ========== steps 3-N: Batch generation Agent Configuration ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]

            report_progress(
                3 + batch_idx,
                t('progress.generatingAgentConfig', start=start_idx + 1, end=end_idx, total=len(entities))
            )

            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)

        reasoning_parts.append(t('progress.agentConfigResult', count=len(all_agent_configs)))

        # ========== Assign a publisher to the initial post Agent ==========
        logger.info("Assign the appropriate publisher to the initial post Agent...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(t('progress.postAssignResult', count=assigned_count))

        # ========== last step: Generate platform configuration ==========
        report_progress(total_steps, t('progress.generatingPlatformConfig'))
        twitter_config = None
        reddit_config = None

        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )

        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )

        # Build final parameters
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )

        logger.info(f"Simulation configuration generation completed: {len(params.agent_configs)} a Agent Configuration")

        return params

    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """build LLM context,Truncate to maximum length"""

        # Entity summary
        entity_summary = self._summarize_entities(entities)

        # Build context
        context_parts = [
            f"## Simulation requirements\n{simulation_requirement}",
            f"\n## Entity information ({len(entities)}a)\n{entity_summary}",
        ]

        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # stay 500 character margin

        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(Document truncated)"
            context_parts.append(f"\n## Original document content\n{doc_text}")

        return "\n".join(context_parts)

    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """Generate entity summary"""
        lines = []

        # Group by type
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)

        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)}a)")
            # Use configured display number and summary length
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... Also {len(type_entities) - display_count} a")

        return "\n".join(lines)

    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """With retry LLM call,contains JSON fix logic"""
        import re

        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                response = create_chat_completion(
                    self.client,
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1),  # Lower the temperature each time you retry
                    # Not set max_tokens,let LLM free play
                )

                content = extract_chat_completion_text(response)
                finish_reason = response.choices[0].finish_reason

                # Check if truncated
                if finish_reason == 'length':
                    logger.warning(f"LLM Output is truncated (attempt {attempt+1})")
                    content = self._fix_truncated_json(content)

                # try to parse JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON Parsing failed (attempt {attempt+1}): {str(e)[:80]}")

                    # try to fix JSON
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed

                    last_error = e

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))

        raise last_error or Exception("LLM call failed")

    def _fix_truncated_json(self, content: str) -> str:
        """fix truncated JSON"""
        content = content.strip()

        # Count unclosed parentheses
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Check if there is an unclosed string
        if content and content[-1] not in '",}]':
            content += '"'

        # closing bracket
        content += ']' * open_brackets
        content += '}' * open_braces

        return content

    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Try to fix configuration JSON"""
        import re

        # Fix truncated cases
        content = self._fix_truncated_json(content)

        # Extract JSON part
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()

            # Remove newline characters from string
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s

            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)

            try:
                return json.loads(json_str)
            except:
                # Try to remove all control characters
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass

        return None

    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """Build time configuration"""
        # Truncate length using configured context
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]

        # Calculate the maximum allowed value(80%of agent number)
        max_agents_allowed = max(1, int(num_entities * 0.9))

        prompt = f"""Based on the following simulation requirements,Build time simulation configuration.

{context_truncated}

## Task
Please generate time configuration JSON.

### basic principles(For reference only,Need to be flexibly adjusted according to specific events and participating groups):
- Infer the target audience's time zone and daily routine from the simulation scenario. The values below are an illustrative local-time schedule.
- early morning 0-5 There is almost no activity(activity coefficient 0.05)
- morning 6-8 dots gradually become active(activity coefficient 0.4)
- working hours 9-18 Moderately active(activity coefficient 0.7)
- Evening 19-22 Point is the peak period(activity coefficient 1.5)
- 23 Activity decreases after clicking(activity coefficient 0.5)
- General rules:Low activity in the early morning,Increasing in the morning,Moderate working hours,evening peak
- **important**:The following example values are for reference only,You need to depend on the nature of the event,Adjust the specific time period based on the characteristics of the participating groups
  - For example:The student population peak may be 21-23 point;Media active throughout the day;Official agencies are only open during working hours
  - For example:Emerging hot topics may lead to discussions late at night,off_peak_hours Can be shortened appropriately

### Return JSON Format(Don t markdown)

Example:
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "Time configuration description for this event"
}}

Field description:
- total_simulation_hours (int): Total simulation time,24-168 hours,Short emergencies,Long lasting topic
- minutes_per_round (int): Duration of each round,30-120 minutes,Suggestions 60 minutes
- agents_per_hour_min (int): Minimum activation per hour Agent number(Value range: 1-{max_agents_allowed})
- agents_per_hour_max (int): Maximum activations per hour Agent number(Value range: 1-{max_agents_allowed})
- peak_hours (int array): peak hours,Adjust according to event participant groups
- off_peak_hours (int array): Trough period,Usually late at night and early in the morning
- morning_hours (int array): morning session
- work_hours (int array): working hours
- reasoning (string): Briefly explain why it is configured this way"""

        system_prompt = "You are a social media simulation expert.Return pure JSON Format,The time configuration must conform to the work and rest habits of the target user groups in the simulation scenario."
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Time configuration LLM Build failed: {e}, Use default configuration")
            return self._get_default_time_config(num_entities)

    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """Get a generic local-time activity configuration."""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # every round 1 hours,Speed up the flow of time
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "Use the generic local-time schedule (one simulated hour per round)"
        }

    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """Parse time configuration results,and verify agents_per_hour The value does not exceed the total agent number"""
        # Get original value
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))

        # Verify and correct:Make sure not to exceed the total agent number
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) more than total Agent number ({num_entities}),Corrected")
            agents_per_hour_min = max(1, num_entities // 10)

        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) more than total Agent number ({num_entities}),Corrected")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)

        # ensure min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max,has been corrected to {agents_per_hour_min}")

        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  # Default every round 1 hours
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # Almost no one in the early morning
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )

    def _generate_event_config(
        self,
        context: str,
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """Generate event configuration"""

        # Get the list of available entity types,supply LLM Reference
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))

        # List representative entity names for each type
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)

        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}"
            for t, examples in type_examples.items()
        ])

        # Truncate length using configured context
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]

        prompt = f"""Based on the following simulation requirements,Generate event configuration.

Simulation requirements: {simulation_requirement}

{context_truncated}

## Available entity types and examples
{type_info}

## Task
Please generate event configuration JSON:
- Extract hot topic keywords
- Describe the direction of public opinion development
- Design initial post content,**Each post must specify poster_type(Publisher type)**

**important**: poster_type must be from above"Available entity types"Select,This way the initial post can be assigned to the appropriate Agent publish.
For example:The official statement should be made by Official/University type release,News by MediaOutlet publish,Student perspective by Student publish.

Return JSON Format(Don t markdown):
{{
    "hot_topics": ["keywords 1", "keywords 2", ...],
    "narrative_direction": "<Description of the development direction of public opinion>",
    "initial_posts": [
        {{"content": "Post content", "poster_type": "Entity type(Must choose from available types)"}},
        ...
    ],
    "reasoning": "<Brief description>"
}}"""

        system_prompt = "You are an expert in public opinion analysis.Return pure JSON Format.Note poster_type Must exactly match available entity types."
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}\nIMPORTANT: The 'poster_type' field value MUST be in English PascalCase exactly matching the available entity types. Only 'content', 'narrative_direction', 'hot_topics' and 'reasoning' fields should use the specified language."

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"event configuration LLM Build failed: {e}, Use default configuration")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "Use default configuration"
            }

    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """Parse event configuration results"""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )

    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        Assign the appropriate publisher to the initial post Agent

        According to each post poster_type Match the most suitable agent_id
        """
        if not event_config.initial_posts:
            return event_config

        # Create by entity type agent Index
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)

        # type mapping table(Process LLM Different formats of possible output)
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }

        # Record the used agent Index,Avoid reusing the same agent
        used_indices: Dict[str, int] = {}

        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")

            # Try to find a match agent
            matched_agent_id = None

            # 1. direct match
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. Use alias matching
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break

            # 3. If still not found,Use the most influential agent
            if matched_agent_id is None:
                logger.warning(f"type not found '{poster_type}' match Agent,Use the most influential Agent")
                if agent_configs:
                    # Sort by influence,Choose the most influential
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0

            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })

            logger.info(f"Initial post allocation: poster_type='{poster_type}' -> agent_id={matched_agent_id}")

        event_config.initial_posts = updated_posts
        return event_config

    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """Batch generation Agent Configuration"""

        # Build entity information(Use configured digest length)
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })

        prompt = f"""Based on the following information,Generate social media activity configuration for each entity.

Simulation requirements: {simulation_requirement}

## Entity list
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## Task
Generate activity configuration for each entity,Note:
- **Match the target audience's schedule**: Treat the hours below as local-time examples and adjust them to the simulation scenario.
- **official agency**(University/GovernmentAgency):Low activity(0.1-0.3),working hours(9-17)Activities,Slow response(60-240 minutes),High influence(2.5-3.0)
- **media**(MediaOutlet):Active(0.4-0.6),All day activities(8-23),Fast response(5-30 minutes),High influence(2.0-2.5)
- **personal**(Student/Person/Alumni):High activity(0.6-0.9),Main evening activities(18-23),Fast response(1-15 minutes),low influence(0.8-1.2)
- **public figure/expert**:Active(0.4-0.6),Medium to high influence(1.5-2.0)

Return JSON Format(Don t markdown):
{{
    "agent_configs": [
        {{
            "agent_id": <Must match the input>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <Posting frequency>,
            "comments_per_hour": <Comment frequency>,
            "active_hours": [<Active hours list based on the target audience's routine>],
            "response_delay_min": <Minimum response delay in minutes>,
            "response_delay_max": <Maximum response delay in minutes>,
            "sentiment_bias": <-1.0 Arrive 1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <influence weight>
        }},
        ...
    ]
}}"""

        system_prompt = "You are an expert in social media behavior analysis.Return pure JSON,The configuration must conform to the work and rest habits of the target user group in the simulation scenario."
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}\nIMPORTANT: The 'stance' field value MUST be one of the English strings: 'supportive', 'opposing', 'neutral', 'observer'. All JSON field names and numeric values must remain unchanged. Only natural language text fields should use the specified language."

        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent configure batch LLM Build failed: {e}, Generate using rules")
            llm_configs = {}

        # build AgentActivityConfig object
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})

            # if LLM Not generated,Generate using rules
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)

            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0)
            )
            configs.append(config)

        return configs

    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """Generate one rule-based agent activity configuration."""
        entity_type = (entity.get_entity_type() or "Unknown").lower()

        if entity_type in ["university", "governmentagency", "ngo"]:
            # official agency:working time activities,low frequency,high impact
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # media:All day activities,medium frequency,high impact
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # expert/Professor:work+Evening activities,medium frequency
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # student:Mainly in the evening,high frequency
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # morning+Evening
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # Alumni:Mainly in the evening
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # lunch break+Evening
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # ordinary people:evening peak
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # daytime+Evening
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
