"""Agent chaining configuration.

Defines which agents auto-trigger which downstream agents after completion.
Toggle chains on/off here without touching agent code.
"""

CHAIN_CONFIG = {
    "news_agent": {
        "next": ["scorer_agent"],
        "condition": "always",
    },
    "scorer_agent": {
        "next": ["analyst_agent"],
        "condition": "score_above_40",
    },
    "analyst_agent": {
        "next": ["seat_agent"],
        "condition": "has_constituencies",
    },
    "seat_agent": {
        "next": [],
        "condition": "terminal",
    },
    "wiki_agent": {
        "next": [],
        "condition": "terminal",
    },
}
