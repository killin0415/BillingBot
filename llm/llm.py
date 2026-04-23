from asyncpg import Connection
from discord import Bot, Message, TextChannel
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionToolUnionParam,
    ChatCompletionMessageFunctionToolCall
)

from datetime import datetime
from typing import Optional

from db import get_db
from repository.chat_repository import ChatRepository
from tools import AVAILABLE_TOOLS

from .config import OpenAIConfig
from .prompt_store import PromptStore
from .types import PossibleMessageType


class LLMService():
    client: AsyncOpenAI
    config: OpenAIConfig
    prompts: PromptStore
    tools: list[ChatCompletionToolUnionParam]

    def __init__(self) -> None:
        self.config = OpenAIConfig()
        self.prompts = PromptStore()

        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )

        self.tools = []
        for tool_cls in AVAILABLE_TOOLS:
            self.tools.extend(tool_cls.get_registered_tools())

    async def _build_messages(
        self,
        conn: Connection,
        bot: Bot,
        channel: TextChannel,
    ) -> list[PossibleMessageType]:
        db_messages = await ChatRepository.get_channel_history(
            conn=conn,
            channel_id=channel.id,
            limit=self.config.max_history_messages * 2
        )

        bot_id = bot.user.id if bot.user else None
        display_name = channel.guild.me.display_name

        system_prompt = self.prompts.get_system_prompt(
            self.config.response_mode)
        messages: list[PossibleMessageType] = [
            {"role": "system", "content": f"The assistant is currently running in a Discord bot with the username {display_name} and user ID {bot_id}. When responding, you can use this information to make your responses more relevant and personalized."},
            {"role": "system", "content": f"Current time: {datetime.now().isoformat()}"},
        ]

        for msg in db_messages:
            if msg.role == "user":
                timestamp = msg.id.datetime.astimezone().isoformat()
                messages.append({
                    "role": "user",
                    "content": f"[{timestamp}][{msg.username}<@{msg.user_id}>]: {msg.content}",
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })  # type: ignore

        messages.append({"role": "system", "content": system_prompt})

        return messages

    async def _chat_create(
        self,
        messages: list[PossibleMessageType]
    ) -> ChatCompletionMessage:
        completion = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
            temperature=1.3,
        )

        return completion.choices[0].message

    async def _call_tools(
        self,
        tool_calls: list[ChatCompletionMessageFunctionToolCall],
        bot: Bot,
        message: Message,
    ) -> list[PossibleMessageType]:
        results: list[PossibleMessageType] = []

        for tool_call in tool_calls:
            func_name = tool_call.function.name

            exec_result: Optional[str] = None
            for tool_cls in AVAILABLE_TOOLS:
                try:
                    exec_result = await tool_cls.call_tool(
                        tool_call=tool_call,
                        bot=bot,
                        message=message,
                    )
                except Exception as e:
                    exec_result = f"Error executing tool {func_name}: {str(e)}"

                if exec_result is not None:
                    break

            if exec_result is None:
                exec_result = f"Unknown tool: {func_name}"

            results.extend([
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                    ]
                },
                {
                    "role": "tool",
                    "content": exec_result,
                    "tool_call_id": tool_call.id
                }
            ])

        return results

    async def _process_message(
        self,
        conn: Connection,
        bot: Bot,
        message: Message,
        channel: TextChannel,
    ) -> tuple[str, ChatCompletionMessage]:
        messages = await self._build_messages(
            conn=conn,
            bot=bot,
            channel=channel,
        )

        final_response: str = ""
        for _ in range(self.config.max_tool_iterations):
            response_message = await self._chat_create(
                messages=messages
            )

            tool_calls = response_message.tool_calls
            if not tool_calls:
                response = response_message.content or response_message.refusal
                final_response = response or "抱歉，我無法生成回應。"
                break

            tool_results = await self._call_tools(
                tool_calls=[
                    tool_call for tool_call in tool_calls
                    if isinstance(tool_call, ChatCompletionMessageFunctionToolCall)
                ],
                bot=bot,
                message=message,
            )

            messages.extend(tool_results)

        if not final_response:
            final_response = "抱歉，我無法生成回應。"

        return final_response, response_message  # type: ignore

    async def process_message(
        self,
        bot: Bot,
        message: Message,
    ) -> str:
        text_channel = message.channel
        if not isinstance(text_channel, TextChannel):
            return "抱歉，我只能在文字頻道中回應。"

        user = message.author

        async with get_db() as conn:
            await ChatRepository.insert(
                conn=conn,
                channel_id=text_channel.id,
                role="user",
                content=message.content,
                user_id=user.id,
                username=user.display_name,
                message_id=message.id
            )

            response, raw_message = await self._process_message(
                conn=conn,
                bot=bot,
                message=message,
                channel=text_channel,
            )

            await ChatRepository.insert(
                conn=conn,
                channel_id=text_channel.id,
                role="assistant",
                content=response,
            )

        return response


_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMService()

    return _service_instance
