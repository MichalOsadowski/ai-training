"""
Budget tracking utility for managing API costs.
"""

from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class CostRecord:
    """Individual cost record."""
    timestamp: datetime
    amount: float
    description: str
    model: str = None
    tokens: int = 0

class BudgetTracker:
    """Tracks API costs and enforces budget limits."""
    
    def __init__(self, budget_limit: float):
        self.budget_limit = budget_limit
        self.costs: List[CostRecord] = []
        self.total_cost = 0.0
    
    def add_cost(self, amount: float, description: str = "API call", model: str = None, tokens: int = 0):
        """Add a cost entry."""
        record = CostRecord(
            timestamp=datetime.now(),
            amount=amount,
            description=description,
            model=model,
            tokens=tokens
        )
        self.costs.append(record)
        self.total_cost += amount
    
    def can_afford(self, amount: float) -> bool:
        """Check if we can afford the given amount."""
        return (self.total_cost + amount) <= self.budget_limit
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget."""
        return max(0, self.budget_limit - self.total_cost)
    
    def get_budget_percentage_used(self) -> float:
        """Get percentage of budget used."""
        if self.budget_limit == 0:
            return 100.0
        return (self.total_cost / self.budget_limit) * 100
    
    def is_budget_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        return self.total_cost > self.budget_limit
    
    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by model."""
        breakdown = {}
        for record in self.costs:
            model = record.model or "unknown"
            breakdown[model] = breakdown.get(model, 0) + record.amount
        return breakdown
    
    def save_to_file(self, filepath: str):
        """Save cost records to file."""
        data = {
            "budget_limit": self.budget_limit,
            "total_cost": self.total_cost,
            "costs": [
                {
                    "timestamp": record.timestamp.isoformat(),
                    "amount": record.amount,
                    "description": record.description,
                    "model": record.model,
                    "tokens": record.tokens
                }
                for record in self.costs
            ]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def __str__(self) -> str:
        return f"Budget: ${self.total_cost:.4f}/${self.budget_limit:.2f} ({self.get_budget_percentage_used():.1f}%)" 