"""
Base LLM provider interface for vendor-agnostic implementation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import tiktoken

@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    tokens_used: int
    cost: float
    model: str

@dataclass
class LLMMessage:
    """Message structure for LLM communication."""
    role: str  # "system", "user", "assistant"
    content: str

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, budget_tracker: 'BudgetTracker'):
        self.api_key = api_key
        self.budget_tracker = budget_tracker
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    
    @abstractmethod
    async def generate(
        self, 
        messages: List[LLMMessage], 
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate response from LLM."""
        pass
    
    @abstractmethod
    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Generate response with system and user prompts."""
        pass
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Estimate cost for token usage."""
        # Default implementation - override in specific providers
        return 0.0
    
    async def check_budget(self, estimated_tokens: int, model: str) -> bool:
        """Check if request is within budget."""
        estimated_cost = self.estimate_cost(estimated_tokens, estimated_tokens, model)
        return self.budget_tracker.can_afford(estimated_cost) 