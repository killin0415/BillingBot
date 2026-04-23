from os import getenv


class OpenAIConfig():
    api_key: str
    base_url: str
    model: str
    max_history_messages: int = 1000
    max_tokens: int = 10_000
    max_tool_iterations: int = 3

    def __init__(self):
        api_key = getenv("OPENAI_API_KEY")
        base_url = getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
        model = getenv("OPENAI_MODEL", "gpt-4-0613")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set in environment variables.")

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_history_messages = int(getenv(
            "OPENAI_MAX_HISTORY_MESSAGES",
            self.max_history_messages
        ))
        self.max_tokens = int(getenv(
            "OPENAI_MAX_TOKENS",
            self.max_tokens
        ))
        self.max_tool_iterations = int(getenv(
            "OPENAI_MAX_TOOL_ITERATIONS",
            self.max_tool_iterations
        ))
