"""
OpenAI LLM provider implementation.
"""

import openai
from typing import List, Optional, Dict, Any
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from .base import BaseLLMProvider, LLMResponse, LLMMessage
from ..utils.budget_tracker import BudgetTracker


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation."""

    # Pricing per 1K tokens (as of 2024)
    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
    }

    def __init__(self, api_key: str, budget_tracker: BudgetTracker, default_model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, budget_tracker)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_model = default_model

    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate response from OpenAI."""

        used_model = model or self.default_model

        # Convert messages to OpenAI format
        openai_messages: List[ChatCompletionMessageParam] = [
            {"role": msg.role, "content": msg.content}  # type: ignore
            for msg in messages
        ]

        # Estimate tokens and check budget
        total_prompt_tokens = sum(self.count_tokens(msg.content)
                                  for msg in messages)
        estimated_cost = self.estimate_cost(
            total_prompt_tokens, max_tokens, used_model)

        if not self.budget_tracker.can_afford(estimated_cost):
            raise Exception(
                f"Request would exceed budget. Estimated cost: ${estimated_cost:.4f}")

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                model=used_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content or ""
            usage = response.usage
            if not usage:
                raise Exception("No usage information in response")

            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens

            actual_cost = self.estimate_cost(
                prompt_tokens, completion_tokens, used_model)
            self.budget_tracker.add_cost(actual_cost)

            return LLMResponse(
                content=content,
                tokens_used=prompt_tokens + completion_tokens,
                cost=actual_cost,
                model=used_model
            )

        except openai.AuthenticationError as e:
            raise Exception(
                f"OpenAI authentication failed. Please check your API key: {str(e)}")
        except openai.RateLimitError as e:
            raise Exception(
                f"OpenAI rate limit exceeded. Please try again later: {str(e)}")
        except openai.BadRequestError as e:
            raise Exception(
                f"OpenAI request failed. Invalid request: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate response with system and user prompts."""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        return await self.generate(messages, model, temperature, max_tokens)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Estimate cost for OpenAI token usage."""
        if model not in self.PRICING:
            model = "gpt-3.5-turbo"  # Default fallback

        pricing = self.PRICING[model]
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]

        return input_cost + output_cost
