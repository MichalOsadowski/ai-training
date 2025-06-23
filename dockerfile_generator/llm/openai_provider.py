"""
OpenAI LLM provider implementation.
"""

import openai
from typing import List, Optional
import asyncio

from .base import BaseLLMProvider, LLMResponse, LLMMessage

class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation."""
    
    # Pricing per 1K tokens (as of 2024)
    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
    }
    
    def __init__(self, api_key: str, budget_tracker: 'BudgetTracker', default_model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, budget_tracker)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_model = default_model
    
    async def generate(
        self, 
        messages: List[LLMMessage], 
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate response from OpenAI."""
        
        model = model or self.default_model
        
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Estimate tokens and check budget
        total_prompt_tokens = sum(self.count_tokens(msg.content) for msg in messages)
        estimated_cost = self.estimate_cost(total_prompt_tokens, max_tokens, model)
        
        if not self.budget_tracker.can_afford(estimated_cost):
            raise Exception(f"Request would exceed budget. Estimated cost: ${estimated_cost:.4f}")
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            
            actual_cost = self.estimate_cost(prompt_tokens, completion_tokens, model)
            self.budget_tracker.add_cost(actual_cost)
            
            return LLMResponse(
                content=content,
                tokens_used=prompt_tokens + completion_tokens,
                cost=actual_cost,
                model=model
            )
            
        except openai.AuthenticationError as e:
            raise Exception(f"OpenAI authentication failed. Please check your API key: {str(e)}")
        except openai.RateLimitError as e:
            raise Exception(f"OpenAI rate limit exceeded. Please try again later: {str(e)}")
        except openai.BadRequestError as e:
            raise Exception(f"OpenAI request failed. Invalid request: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
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