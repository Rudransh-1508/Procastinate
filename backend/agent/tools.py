"""Tool schemas in OpenAI/Groq function-calling format.

The agent calls these to *get* data — it never fabricates numbers. The
executor (tool_executor.py) implements them against the DB and analyzer.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_procrastination_events",
            "description": "Query logged procrastination events with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Filter by task type"},
                    "days_back": {"type": "integer", "description": "How many days to look back"},
                    "displacement_type": {"type": "string"},
                    "min_delay_hours": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_profile_state",
            "description": "Get the current persistent user profile model.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_pattern_analysis",
            "description": "Run statistical pattern analysis on logged events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": [
                            "avoidance_by_type",
                            "temporal_heatmap",
                            "trigger_effectiveness",
                            "displacement_distribution",
                            "correlation_matrix",
                        ],
                    }
                },
                "required": ["analysis_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile_state",
            "description": "Update the persistent user profile with a new insight or field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "value": {"description": "The value to store (any JSON type)"},
                    "reason": {"type": "string"},
                },
                "required": ["field", "value", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_details",
            "description": "Get full details of a specific task including its history.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        },
    },
]
