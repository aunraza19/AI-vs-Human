from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicProfile:
    topic_id: str
    title: str
    persona: str
    stance: str
    framing: str


TOPIC_PROFILES: tuple[TopicProfile, ...] = (
    TopicProfile(
        topic_id="ai-education",
        title="AI Should Be Mandatory in Schools",
        persona="an education technologist",
        stance="FOR",
        framing="AI literacy is now as fundamental as digital literacy.",
    ),
    TopicProfile(
        topic_id="remote-work",
        title="Remote Work Is Better Than Office Work",
        persona="a workplace productivity researcher",
        stance="FOR",
        framing="Flexible work structures improve output and wellbeing.",
    ),
    TopicProfile(
        topic_id="social-media-age-limit",
        title="Social Media Should Be 16+ Only",
        persona="a child development psychologist",
        stance="FOR",
        framing="Adolescent attention and mental health need stronger boundaries.",
    ),
    TopicProfile(
        topic_id="nuclear-energy",
        title="Nuclear Power Is Essential for Climate Goals",
        persona="a climate policy scientist",
        stance="FOR",
        framing="Grid-scale decarbonization requires dependable baseload generation.",
    ),
    TopicProfile(
        topic_id="four-day-week",
        title="A Four-Day Workweek Should Be the New Standard",
        persona="a labor economist",
        stance="FOR",
        framing="Productivity can hold while burnout and attrition drop.",
    ),
)

TOPICS_BY_ID: dict[str, TopicProfile] = {topic.topic_id: topic for topic in TOPIC_PROFILES}
DEFAULT_TOPIC_ID = TOPIC_PROFILES[0].topic_id


def get_topic(topic_id: str | None) -> TopicProfile:
    if not topic_id:
        return TOPICS_BY_ID[DEFAULT_TOPIC_ID]
    return TOPICS_BY_ID.get(topic_id, TOPICS_BY_ID[DEFAULT_TOPIC_ID])


def topic_exists(topic_id: str) -> bool:
    return topic_id in TOPICS_BY_ID


def list_topics() -> list[dict[str, str]]:
    return [
        {
            "topic_id": topic.topic_id,
            "title": topic.title,
            "persona": topic.persona,
            "stance": topic.stance,
            "framing": topic.framing,
        }
        for topic in TOPIC_PROFILES
    ]
