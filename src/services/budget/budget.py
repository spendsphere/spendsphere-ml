import json
import requests
from pathlib import Path
from datetime import datetime
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434"


class TimePeriod(Enum):
    ONE_MONTH = 1
    THREE_MONTHS = 3
    SIX_MONTHS = 6
    ONE_YEAR = 12


class BudgetAnalysisService:
    """AI-powered budget analysis and financial advice service."""

    def __init__(self, base_url: str = OLLAMA_API_URL, model: str = "qwen3:14b"):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()

    def load_json(self, path: str) -> dict:
        """Load JSON file from disk."""
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading JSON from {path}: {e}")
            raise

    def load_prompt(self, path: str) -> str:
        """Load prompt text from disk."""
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except FileNotFoundError as e:
            logger.error(f"Error loading prompt from {path}: {e}")
            raise

    def call_ollama_api(self, payload: dict) -> dict:
        """Make API call to Ollama."""
        try:
            resp = self.session.post(f"{self.base_url}/api/chat", json=payload, timeout=10000)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API call failed: {e}")
            raise

    def validate_financial_data(self, financial_data: dict) -> bool:
        """Validate the structure of financial data."""
        required_sections = ['income', 'expenses', 'savings', 'debts']

        if not all(section in financial_data for section in required_sections):
            logger.error(f"Missing required sections. Required: {required_sections}")
            return False

        # Validate income structure
        if not isinstance(financial_data['income'], dict):
            logger.error("Income should be a dictionary")
            return False

        # Validate expenses structure
        if not isinstance(financial_data['expenses'], dict):
            logger.error("Expenses should be a dictionary")
            return False

        return True

    def calculate_financial_metrics(self, financial_data: dict) -> dict[str, float]:
        """Calculate key financial metrics."""
        total_income = sum(financial_data['income'].values())
        total_expenses = sum(financial_data['expenses'].values())

        # Calculate expense categories
        essential_expenses = sum(
            financial_data['expenses'].get(category, 0)
            for category in ['housing', 'utilities', 'food', 'transportation', 'insurance']
        )

        discretionary_expenses = total_expenses - essential_expenses

        metrics = {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_cash_flow': total_income - total_expenses,
            'savings_rate': ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0,
            'essential_expenses_ratio': (essential_expenses / total_income * 100) if total_income > 0 else 0,
            'discretionary_expenses_ratio': (discretionary_expenses / total_income * 100) if total_income > 0 else 0,
            'debt_to_income_ratio': (
                        sum(financial_data['debts'].values()) / total_income * 100) if total_income > 0 else 0
        }

        return metrics

    def analyze_budget(self, financial_data: dict,
                       time_period: TimePeriod = TimePeriod.ONE_MONTH,
                       user_goals: None | list[str] = None) -> dict:
        """
        Analyze financial data and provide AI-powered budget advice.

        Args:
            financial_data: Dictionary containing income, expenses, savings, debts
            time_period: Time period for analysis
            user_goals: Optional list of user financial goals

        Returns:
            Dict containing analysis and recommendations
        """
        logger.info(f"Starting budget analysis for {time_period.value} month(s)")

        # Validate input data
        if not self.validate_financial_data(financial_data):
            raise ValueError("Invalid financial data structure")

        # Calculate financial metrics
        metrics = self.calculate_financial_metrics(financial_data)

        # Load schema and prompt
        schema = self.load_json("schemas/budget_analysis_schema.json")
        prompt = self.load_prompt("prompts/budget_analysis_prompt.txt")

        # Prepare context for AI
        context = {
            "financial_data": financial_data,
            "metrics": metrics,
            "time_period_months": time_period.value,
            "user_goals": user_goals or [],
            "analysis_date": datetime.now().isoformat()
        }

        messages = [
            {
                "role": "system",
                "content": "You are a expert financial advisor with deep knowledge of personal finance, budgeting, and wealth building. Provide practical, actionable advice."
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nFinancial Context:\n{json.dumps(context, indent=2, ensure_ascii=False)}"
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema
        }

        response_data = self.call_ollama_api(payload)
        content_str = response_data["message"]["content"]

        try:
            analysis_result = json.loads(content_str)
            # Add calculated metrics to the result
            analysis_result['financial_metrics'] = metrics
            return analysis_result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {content_str}")
            raise

    def generate_spending_plan(self, financial_data: dict,
                               target_savings_rate: float = 20.0) -> dict:
        """
        Generate a detailed spending plan to achieve target savings rate.

        Args:
            financial_data: User's financial data
            target_savings_rate: Desired savings rate percentage

        Returns:
            Dict containing optimized spending plan
        """
        schema = self.load_json("schemas/spending_plan_schema.json")
        prompt = self.load_prompt("prompts/spending_plan_prompt.txt")

        metrics = self.calculate_financial_metrics(financial_data)

        context = {
            "current_financial_data": financial_data,
            "current_metrics": metrics,
            "target_savings_rate": target_savings_rate
        }

        messages = [
            {
                "role": "system",
                "content": "You are a budgeting expert. Create realistic, achievable spending plans that help users reach their financial goals."
            },
            {
                "role": "user",
                "content": f"{prompt}\n\n{json.dumps(context, indent=2, ensure_ascii=False)}"
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema
        }

        response_data = self.call_ollama_api(payload)
        content_str = response_data["message"]["content"]

        return json.loads(content_str)

    def compare_periods(self, current_data: dict,
                        previous_data: dict) -> dict:
        """
        Compare financial data between two periods and analyze trends.
        """
        schema = self.load_json("schemas/period_comparison_schema.json")
        prompt = self.load_prompt("prompts/period_comparison_prompt.txt")

        current_metrics = self.calculate_financial_metrics(current_data)
        previous_metrics = self.calculate_financial_metrics(previous_data)

        context = {
            "current_period": {
                "data": current_data,
                "metrics": current_metrics
            },
            "previous_period": {
                "data": previous_data,
                "metrics": previous_metrics
            }
        }

        messages = [
            {
                "role": "system",
                "content": "You are a financial analyst. Identify trends, improvements, and areas of concern in financial data across time periods."
            },
            {
                "role": "user",
                "content": f"{prompt}\n\n{json.dumps(context, indent=2, ensure_ascii=False)}"
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": schema
        }

        response_data = self.call_ollama_api(payload)
        content_str = response_data["message"]["content"]

        return json.loads(content_str)


# Example usage and data templates
def create_sample_financial_data() -> dict:
    """Create sample financial data for testing."""
    return {
        "income": {
            "salary": 5000.00,
            "freelance": 1000.00,
            "investments": 200.00
        },
        "expenses": {
            "housing": 1500.00,
            "utilities": 300.00,
            "food": 600.00,
            "transportation": 400.00,
            "entertainment": 300.00,
            "shopping": 400.00,
            "insurance": 250.00,
            "subscriptions": 100.00
        },
        "savings": {
            "emergency_fund": 5000.00,
            "retirement": 15000.00,
            "investment_account": 3000.00
        },
        "debts": {
            "student_loans": 20000.00,
            "credit_cards": 5000.00,
            "car_loan": 10000.00
        }
    }


def main():
    """Example usage of the Budget Analysis Service."""
    service = BudgetAnalysisService()

    try:
        # Sample financial data
        financial_data = create_sample_financial_data()
        user_goals = ["Build emergency fund", "Pay off credit card debt", "Save for vacation"]

        # Analyze budget
        analysis = service.analyze_budget(
            financial_data=financial_data,
            time_period=TimePeriod.THREE_MONTHS,
            user_goals=user_goals
        )

        print("Budget Analysis Result:")
        print(json.dumps(analysis, indent=2, ensure_ascii=False))

        # Generate spending plan
        spending_plan = service.generate_spending_plan(
            financial_data=financial_data,
            target_savings_rate=25.0
        )

        print("\nSpending Plan:")
        print(json.dumps(spending_plan, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Budget analysis failed: {e}")


if __name__ == "__main__":
    main()