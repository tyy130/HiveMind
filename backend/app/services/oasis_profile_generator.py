"""
OASIS Agent Profile generator
will Zep Entities in the graph are converted to OASIS Required for simulation platform Agent Profile Format

Optimization and improvement:
1. call Zep Search function enriches node information twice
2. Optimize prompt words to generate very detailed characters
3. Distinguish between personal entities and abstract group entities
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, get_locale, set_locale, t
from ..utils.openai_chat_compat import create_chat_completion, extract_chat_completion_text
from ..utils.zep import (
    call_zep_read_with_retry,
    get_zep_client,
    is_retryable_zep_error,
    normalize_zep_search_query,
)
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.oasis_profile')


def _coerce_to_str(value: Any) -> str:
    """Coerce a value to a plain string.

    Handles dict, list, and other non-string types that may be returned
    by LLM JSON parsing.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ('text', 'value', 'description', 'content', 'summary', 'name'):
            if key in value:
                candidate = _coerce_to_str(value[key])
                if candidate:
                    return candidate
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        str_items = [_coerce_to_str(item) for item in value]
        str_items = [item for item in str_items if item]
        return ', '.join(str_items)
    return str(value)


def _coerce_to_str_list(value: Any) -> List[str]:
    """Coerce a value to a list of strings.

    Handles nested structures that may be returned by LLM JSON parsing.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        result: List[str] = []
        for item in value:
            if isinstance(item, (list, tuple)):
                result.extend(_coerce_to_str_list(item))
            else:
                text = _coerce_to_str(item)
                if text:
                    result.append(text)
        return result
    text = _coerce_to_str(value)
    return [text] if text else []


@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile data structure"""
    # Common fields
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str

    # optional fields - Reddit style
    karma: int = 1000

    # optional fields - Twitter style
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500

    # Additional character information
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)

    # Source entity information
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None

    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def __post_init__(self):
        """Normalize structured LLM fields once at the profile boundary."""
        self.bio = _coerce_to_str(self.bio) or self.name
        self.persona = _coerce_to_str(self.persona) or (
            f"{self.name} is a participant in social discussions."
        )
        self.country = _coerce_to_str(self.country) or None
        self.profession = _coerce_to_str(self.profession) or None
        self.gender = _coerce_to_str(self.gender) or None
        self.mbti = _coerce_to_str(self.mbti) or None
        self.interested_topics = _coerce_to_str_list(self.interested_topics)

    def to_reddit_format(self) -> Dict[str, Any]:
        """Convert to Reddit platform format"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS The library requires the field name to be username(no underline)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }

        # Add additional personality information(if there is)
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics

        return profile

    def to_twitter_format(self) -> Dict[str, Any]:
        """Convert to Twitter platform format"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS The library requires the field name to be username(no underline)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }

        # Add additional personality information
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics

        return profile

    def to_dict(self) -> Dict[str, Any]:
        """Convert to full dictionary format"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile generator

    will Zep Entities in the graph are converted to OASIS required for simulation Agent Profile

    Optimization features:
    1. call Zep Graph search capabilities for richer context
    2. Generate highly detailed personas(Include basic information,Career experience,Character traits,social media behavior etc)
    3. Distinguish between personal entities and abstract group entities
    """

    # MBTI Type list
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]

    # List of common countries
    COUNTRIES = [
        "China", "US", "UK", "Japan", "Germany", "France",
        "Canada", "Australia", "Brazil", "India", "South Korea"
    ]

    # Person type entity(Need to generate specific persona)
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure",
        "expert", "faculty", "official", "journalist", "activist"
    ]

    # group/Organization type entity(Need to generate group representative persona)
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo",
        "mediaoutlet", "company", "institution", "group", "community"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None
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

        # Zep Client used to retrieve rich context
        self.zep_api_key = zep_api_key or Config.ZEP_API_KEY
        self.zep_client = None
        self.graph_id = graph_id

        if self.zep_api_key:
            try:
                self.zep_client = get_zep_client(self.zep_api_key)
            except Exception as e:
                logger.warning(f"Zep Client initialization failed: {e}")

    def generate_profile_from_entity(
        self,
        entity: EntityNode,
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        from Zep Entity generation OASIS Agent Profile

        Args:
            entity: Zep entity node
            user_id: User ID(used for OASIS)
            use_llm: Whether to use LLM Generate detailed persona

        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"

        # Basic information
        name = entity.name
        user_name = self._generate_username(name)

        # Build contextual information
        context = self._build_entity_context(entity)

        if use_llm:
            # use LLM Generate detailed persona
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context
            )
        else:
            # Use rules to generate basic characters
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )

        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )

    def _generate_username(self, name: str) -> str:
        """Generate username"""
        # Remove special characters,Convert to lowercase
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')

        # Add random suffix to avoid duplication
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"

    def _search_zep_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        use Zep Graph hybrid search function obtains rich information related to entities

        Zep No built-in hybrid search interface,Need to search separately edges and nodes Then merge the results.
        Search simultaneously using parallel requests,Improve efficiency.

        Args:
            entity: entity node object

        Returns:
            contains facts, node_summaries, context dictionary
        """
        import concurrent.futures

        if not self.zep_client:
            return {"facts": [], "node_summaries": [], "context": ""}

        entity_name = entity.name

        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }

        # Must have graph_id to search
        if not self.graph_id:
            logger.debug(f"skip Zep Search:not set graph_id")
            return results

        comprehensive_query = normalize_zep_search_query(
            t('progress.zepSearchQuery', name=entity_name)
        )

        def search_edges():
            """search edge(facts/relationship)- With retry mechanism"""
            return call_zep_read_with_retry(
                lambda: self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=30,
                        scope="edges",
                        reranker="rrf"
                ),
                operation_name=f"profile edge search ({entity.uuid})",
            )

        def search_nodes():
            """Search node(Entity summary)- With retry mechanism"""
            return call_zep_read_with_retry(
                lambda: self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=20,
                        scope="nodes",
                        reranker="rrf"
                ),
                operation_name=f"profile node search ({entity.uuid})",
            )

        try:
            # Parallel execution edges and nodes Search
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)

                # Get results
                # Each request already has the configured HTTP timeout and
                # typed retry budget. A second hard-coded 30s future timeout
                # discarded late successes while the executor still waited.
                edge_result = edge_future.result()
                node_result = node_future.result()

            # Processing edge search results
            all_facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        all_facts.add(edge.fact)
            results["facts"] = list(all_facts)

            # Process node search results
            all_summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        all_summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name != entity_name:
                        all_summaries.add(f"related entities: {node.name}")
            results["node_summaries"] = list(all_summaries)

            # Build comprehensive context
            context_parts = []
            if results["facts"]:
                context_parts.append("factual information:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("related entities:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)

            logger.info(f"Zep Mixed search completed: {entity_name}, get {len(results['facts'])} facts, {len(results['node_summaries'])} related nodes")

        except Exception as e:
            logger.warning(f"Zep Retrieval failed ({entity_name}): {e}")
            if not is_retryable_zep_error(e):
                raise

        return results

    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        Build complete contextual information for an entity

        include:
        1. Side information of the entity itself(facts)
        2. Details of the associated node
        3. Zep Mix the rich information retrieved
        """
        context_parts = []

        # 1. Add entity attribute information
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### Entity properties\n" + "\n".join(attrs))

        # 2. Add relevant side information(facts/relationship)
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:  # No limit on quantity
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")

                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (related entities)")
                    else:
                        relationships.append(f"- (related entities) --[{edge_name}]--> {entity.name}")

            if relationships:
                context_parts.append("### Relevant facts and relationships\n" + "\n".join(relationships))

        # 3. Add details about associated nodes
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:  # No limit on quantity
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")

                # Filter out default tags
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""

                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")

            if related_info:
                context_parts.append("### Related entity information\n" + "\n".join(related_info))

        # 4. use Zep Hybrid search for richer information
        zep_results = self._search_zep_for_entity(entity)

        if zep_results.get("facts"):
            # Remove duplicates:exclude existing facts
            new_facts = [f for f in zep_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Zep Factual information retrieved\n" + "\n".join(f"- {f}" for f in new_facts[:15]))

        if zep_results.get("node_summaries"):
            context_parts.append("### Zep Retrieved related nodes\n" + "\n".join(f"- {s}" for s in zep_results["node_summaries"][:10]))

        return "\n\n".join(context_parts)

    def _is_individual_entity(self, entity_type: str) -> bool:
        """Determine whether it is a personal type entity"""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES

    def _is_group_entity(self, entity_type: str) -> bool:
        """Determine whether it is a group/Organization type entity"""
        return entity_type.lower() in self.GROUP_ENTITY_TYPES

    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        use LLM Generate highly detailed personas

        Distinguish based on entity type:
        - personal entity:Generate specific character settings
        - group/institutional entity:Generate representative account settings
        """

        is_individual = self._is_individual_entity(entity_type)

        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )

        # Try to generate multiple times,Until successful or maximum retries reached
        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                response = create_chat_completion(
                    self.client,
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1),  # Lower the temperature each time you retry
                    # Not set max_tokens,let LLM free play
                )

                content = extract_chat_completion_text(response)

                # Check if truncated(finish_reason No'stop')
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM Output is truncated (attempt {attempt+1}), try to fix...")
                    content = self._fix_truncated_json(content)

                # try to parse JSON
                try:
                    result = json.loads(content)

                    # Validate required fields
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name}is a{entity_type}."

                    return result

                except json.JSONDecodeError as je:
                    logger.warning(f"JSON Parsing failed (attempt {attempt+1}): {str(je)[:80]}")

                    # try to fix JSON
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result

                    last_error = je

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))  # exponential backoff

        logger.warning(f"LLM Failed to generate character({max_attempts}attempts): {last_error}, Generate using rules")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )

    def _fix_truncated_json(self, content: str) -> str:
        """fix truncated JSON(The output is max_tokens Limit truncation)"""
        import re

        # if JSON truncated,try to close it
        content = content.strip()

        # Count unclosed parentheses
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Check if there is an unclosed string
        # simple check:If there is no comma or closing parenthesis after the last quotation mark,Maybe the string was truncated
        if content and content[-1] not in '",}]':
            # Try to close the string
            content += '"'

        # closing bracket
        content += ']' * open_brackets
        content += '}' * open_braces

        return content

    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """Try to repair the broken JSON"""
        import re

        # 1. First try to fix the truncated case
        content = self._fix_truncated_json(content)

        # 2. Try to extract JSON part
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()

            # 3. Dealing with newline characters in strings
            # Find all string values and replace newlines in them
            def fix_string_newlines(match):
                s = match.group(0)
                # Replace actual newlines within a string with spaces
                s = s.replace('\n', ' ').replace('\r', ' ')
                # Replace extra spaces
                s = re.sub(r'\s+', ' ', s)
                return s

            # match JSON string value
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)

            # 4. try to parse
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. If it still fails,Try a more radical fix
                try:
                    # Remove all control characters
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # Replace all consecutive whitespace
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass

        # 6. Try to extract some information from the content
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content)  # may be truncated

        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name}is a{entity_type}.")

        # If meaningful content is extracted,Mark as fixed
        if bio_match or persona_match:
            logger.info(f"from damaged JSON Some information was extracted from")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }

        # 7. complete failure,Return to infrastructure
        logger.warning(f"JSON Repair failed,Return to infrastructure")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name}is a{entity_type}."
        }

    def _get_system_prompt(self, is_individual: bool) -> str:
        """Get system prompt words"""
        base_prompt = "You are an expert in generating social media personas.Generate detailed,Real characters are used for public opinion simulation,Restore existing reality to the greatest extent possible.Must return a valid JSON Format,All string values cannot contain unescaped newlines."
        return f"{base_prompt}\n\n{get_language_instruction()}"

    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Construct detailed personality prompts for personal entities"""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "no additional context"

        return f"""Generate detailed social media personas for entities,Restore existing reality to the greatest extent possible.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity properties: {attrs_str}

contextual information:
{context_str}

Please generate JSON,Contains the following fields:

1. bio: Introduction to social media,200 word
2. persona: Detailed character description(2000 plain text of word),Need to include:
   - Basic information(age,Career,Educational background,location)
   - Character background(important experience,association with events,social relations)
   - Character traits(MBTI Type,core character,emotional expression)
   - social media behavior(Posting frequency,Content preferences,interactive style,language features)
   - standpoint(attitude towards the topic,may be irritated/touching content)
   - unique characteristics(mantra,special experience,personal hobbies)
   - personal memory(important part of personality,To introduce the relationship between this individual and the event,and the individual s actions and reactions in the event)
3. age: age number(Must be an integer)
4. gender: gender,Must be in English: "male" or "female"
5. mbti: MBTI Type(Such as INTJ,ENFP Wait)
6. country: country name in English (for example, "Canada")
7. profession: Career
8. interested_topics: array of interesting topics

important:
- All field values must be strings or numbers,Don t use newline characters
- persona Must be a coherent text description
- {get_language_instruction()} (gender Fields must be in English male/female)
- Content should be consistent with entity information
- age Must be a valid integer,gender must be"male"or"female"
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Build a group/Detailed personal prompts for institutional entities"""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "no additional context"

        return f"""for institutions/Group entities generate detailed social media account settings,Restore existing reality to the greatest extent possible.

Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity properties: {attrs_str}

contextual information:
{context_str}

Please generate JSON,Contains the following fields:

1. bio: Official account introduction,200 word,Professional and decent
2. persona: Detailed account setting description(2000 plain text of word),Need to include:
   - Basic information of the organization(official name,Institutional nature,Establishment background,Main functions)
   - Account positioning(Account type,target audience,Core functions)
   - speaking style(language features,Common expressions,Taboo topics)
   - Features of published content(Content type,Release frequency,Active time period)
   - stance(Official stance on core topics,How to deal with disputes)
   - Special instructions(Portrait of a representative group,Operational habits)
   - institutional memory(An important part of the organization s personality,To introduce the relationship between this organization and the event,and the organization s actions and reactions during the incident)
3. age: Fixed filling 30(Virtual age of organization account)
4. gender: Fixed filling"other"(Institutional account use other means impersonal)
5. mbti: MBTI Type,Used to describe account style,Such as ISTJ Represents strictness and conservatism
6. country: country name in English (for example, "Canada")
7. profession: Organizational Function Description
8. interested_topics: Focus area array

important:
- All field values must be strings or numbers,not allowed null value
- persona Must be a coherent text description,Don t use newline characters
- {get_language_instruction()} (gender Fields must be in English"other")
- age Must be an integer 30,gender Must be a string"other"
- Speeches from institutional accounts must conform to their identity and positioning"""

    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use rules to generate basic characters"""

        # Generate different personas based on entity types
        entity_type_lower = entity_type.lower()

        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} with interests in academics and social issues.",
                "persona": f"{entity_name} is a {entity_type.lower()} who is actively engaged in academic and social discussions. They enjoy sharing perspectives and connecting with peers.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Student",
                "interested_topics": ["Education", "Social Issues", "Technology"],
            }

        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": f"Expert and thought leader in their field.",
                "persona": f"{entity_name} is a recognized {entity_type.lower()} who shares insights and opinions on important matters. They are known for their expertise and influence in public discourse.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Expert"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
            }

        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30,  # Institutional virtual age
                "gender": "other",  # Institutional use other
                "mbti": "ISTJ",  # institutional style:Strict and conservative
                "country": entity_attributes.get("country", "Unknown"),
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
            }

        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30,  # Institutional virtual age
                "gender": "other",  # Institutional use other
                "mbti": "ISTJ",  # institutional style:Strict and conservative
                "country": entity_attributes.get("country", "Unknown"),
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
            }

        else:
            # Default persona
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
            }

    def set_graph_id(self, graph_id: str):
        """Set up the map ID used for Zep Search"""
        self.graph_id = graph_id

    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit"
    ) -> List[OasisAgentProfile]:
        """
        Generate from entities in batches Agent Profile(Supports parallel builds)

        Args:
            entities: Entity list
            use_llm: Whether to use LLM Generate detailed persona
            progress_callback: Progress callback function (current, total, message)
            graph_id: Atlas ID,used for Zep Search for richer context
            parallel_count: Number of parallel builds,Default 5
            realtime_output_path: File path written in real time(If provided,Write every time one is generated)
            output_platform: Output platform format ("reddit" or "twitter")

        Returns:
            Agent Profile list
        """
        import concurrent.futures
        from threading import Lock

        # settings graph_id used for Zep Search
        if graph_id:
            self.graph_id = graph_id

        total = len(entities)
        profiles = [None] * total  # Pre-allocated list maintains order
        completed_count = [0]  # Use lists for modification in closures
        lock = Lock()

        # Auxiliary function for writing files in real time
        def save_profiles_realtime():
            """Save the generated profiles to file"""
            if not realtime_output_path:
                return

            with lock:
                # Filter out generated profiles
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return

                try:
                    if output_platform == "reddit":
                        # Reddit JSON Format
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        # Twitter CSV Format
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"Save in real time profiles failed: {e}")

        # Capture locale before spawning thread pool workers
        current_locale = get_locale()

        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """Generate a single profile working function"""
            set_locale(current_locale)
            entity_type = entity.get_entity_type() or "Entity"

            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )

                # Real-time output of the generated personality to the console and logs
                self._print_generated_profile(entity.name, entity_type, profile)

                return idx, profile, None

            except Exception as e:
                logger.error(f"Generate entity {entity.name} The persona failed: {str(e)}")
                # create a base profile
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)

        logger.info(f"Start parallel build {total} a Agent Personality(Parallel number: {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Start generating Agent Personality - total {total} entities,Parallel number: {parallel_count}")
        print(f"{'='*60}\n")

        # Parallel execution using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # Submit all tasks
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"

                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile

                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]

                    # Write files in real time
                    save_profiles_realtime()

                    if progress_callback:
                        progress_callback(
                            current,
                            total,
                            f"Completed {current}/{total}: {entity.name}({entity_type})"
                        )

                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} Use alternate persona: {error}")
                    else:
                        logger.info(f"[{current}/{total}] Successfully generated character: {entity.name} ({entity_type})")

                except Exception as e:
                    logger.error(f"Handle entities {entity.name} Exception occurs when: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # Write files in real time(Even if it s a backup persona)
                    save_profiles_realtime()

        print(f"\n{'='*60}")
        print(f"Character generation completed!symbiosis {len([p for p in profiles if p])} a Agent")
        print(f"{'='*60}\n")

        return profiles

    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """Output the generated personality to the console in real time(full content,Do not truncate)"""
        separator = "-" * 70

        # Build complete output content(Do not truncate)
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else 'None'

        output_lines = [
            f"\n{separator}",
            t('progress.profileGenerated', name=entity_name, type=entity_type),
            f"{separator}",
            f"Username: {profile.user_name}",
            f"",
            f"[Introduction]",
            f"{profile.bio}",
            f"",
            f"[Detailed character design]",
            f"{profile.persona}",
            f"",
            f"[Basic properties]",
            f"age: {profile.age} | gender: {profile.gender} | MBTI: {profile.mbti}",
            f"Career: {profile.profession} | country: {profile.country}",
            f"Interesting topics: {topics_str}",
            separator
        ]

        output = "\n".join(output_lines)

        # Only output to console(avoid duplication,logger No longer output the complete content)
        print(output)

    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        save Profile to file(Choose the right format based on your platform)

        OASIS Platform format requirements:
        - Twitter: CSV Format
        - Reddit: JSON Format

        Args:
            profiles: Profile list
            file_path: file path
            platform: platform type ("reddit" or "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)

    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        save Twitter Profile for CSV Format(conform to OASIS official request)

        OASIS Twitter required CSV Field:
        - user_id: User ID(According to CSV order from 0 start)
        - name: User real name
        - username: Username in the system
        - user_char: Detailed character description(Inject into LLM System prompts,guidance Agent behavior)
        - description: short public profile(Displayed on user profile page)

        user_char vs description difference:
        - user_char: Internal use,LLM System prompt,decide Agent how to think and act
        - description: external display,Profile visible to other users
        """
        import csv

        # Make sure the file extension is.csv
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # write OASIS required header
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)

            # Write data row
            for idx, profile in enumerate(profiles):
                # user_char: Complete character(bio + persona),used for LLM System prompt
                user_char = profile.bio
                if profile.persona and profile.persona != profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                # Handling newlines(CSV Replace with spaces in)
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')

                # description: short introduction,for external display
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')

                row = [
                    idx,                    # user_id: from 0 starting order ID
                    profile.name,           # name: real name
                    profile.user_name,      # username: Username
                    user_char,              # user_char: Complete character(internal LLM use)
                    description             # description: short introduction(external display)
                ]
                writer.writerow(row)

        logger.info(f"saved {len(profiles)} a Twitter Profile Arrive {file_path} (OASIS CSV Format)")

    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        Standardization gender The fields are OASIS Required English format

        OASIS request: male, female, other
        """
        if not gender:
            return "other"

        gender_lower = gender.lower().strip()

        # Normalize supported values to the OASIS schema.
        gender_map = {
            "male": "male",
            "female": "female",
            "institution": "other",
            "others": "other",
            "other": "other",
        }

        return gender_map.get(gender_lower, "other")

    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        save Reddit Profile for JSON Format

        Use with to_reddit_format() consistent format,ensure OASIS can be read correctly.
        must contain user_id Field,This is OASIS agent_graph.get_agent() matching key!

        Required fields:
        - user_id: User ID(integer,for matching initial_posts in poster_agent_id)
        - username: Username
        - name: display name
        - bio: Introduction
        - persona: Detailed character design
        - age: age(integer)
        - gender: "male", "female", or "other"
        - mbti: MBTI Type
        - country: country
        """
        data = []
        for idx, profile in enumerate(profiles):
            # Use with to_reddit_format() consistent format
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx,  # key:must contain user_id
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150],
                "persona": profile.persona,
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                # OASIS Required fields - Make sure there are default values
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "Unknown",
            }

            # optional fields
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics

            data.append(item)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"saved {len(profiles)} a Reddit Profile Arrive {file_path} (JSON Format,contains user_id Field)")

    # Keep old method names as aliases,Stay backwards compatible
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[Deprecated] Please use save_profiles() method"""
        logger.warning("save_profiles_to_json Deprecated,Please use save_profiles method")
        self.save_profiles(profiles, file_path, platform)
