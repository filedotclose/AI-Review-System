import logging
import time
import json
from enum import Enum
from typing import Dict, Any, Optional

from app.core.config import settings
from app.schemas.ai_schemas import AIReviewResult, RiskLevel

logger = logging.getLogger(__name__)

class AIProvider(str, Enum):
    GEMINI = "GEMINI"
    GROQ = "GROQ"
    NONE = "NONE"

class AIVerificationService:
    """
    AI verification service for construction daily operations review.
    Supports multiple LLM backends (Gemini, Groq) and a rule-based fallback.
    """

    def __init__(self):
        """
        Initializes the AI Verification Service.
        Reads provider and keys from the configuration.
        """
        # Ensure fallback to NONE if setting not present
        self.provider_str = getattr(settings, "AI_PROVIDER", "NONE")
        try:
            self.provider = AIProvider(self.provider_str.upper())
        except ValueError:
            self.provider = AIProvider.NONE
            
        self.gemini_api_key = getattr(settings, "GEMINI_API_KEY", None)
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", None)

    def _is_configured(self) -> bool:
        """
        Checks if the chosen provider has the required API key set.
        """
        if self.provider == AIProvider.GEMINI and self.gemini_api_key:
            return True
        if self.provider == AIProvider.GROQ and self.groq_api_key:
            return True
        return False

    def _build_construction_prompt(self, brief_data: Dict[str, Any]) -> str:
        """
        Builds a domain-specific prompt for construction operations.
        Includes context about heavy civil infrastructure, fuel dip stock, petty cash, etc.
        """
        return f"""
        You are an expert AI Construction Project Manager analyzing a daily site brief.
        Context: The project involves bored piling, deep well foundations, and heavy civil infrastructure.
        Key areas of analysis:
        - Fuel dip stock reconciliation: check for discrepancies between recorded consumption and actual dips.
        - Petty cash deficit tracking: flag any unusual expenditures or low balances.
        - Attendance/manpower analysis: assess if the manpower is sufficient for the reported progress.
        - Anomalies: identify any inconsistencies in construction metrics, safety reports, or material usage.
        
        Analyze the following daily brief data and provide a structured JSON response matching the required schema.
        
        Daily Brief Data:
        {json.dumps(brief_data, indent=2)}
        """

    def _fallback_rule_based_review(self, brief_data: Dict[str, Any]) -> AIReviewResult:
        """
        Provides a deterministic fallback review if AI verification fails or is not configured.
        """
        logger.info("Using rule-based fallback for AI review.")
        
        # Simple heuristics
        alerts = brief_data.get("alerts", [])
        risk_level = RiskLevel.LOW
        if len(alerts) > 5:
            risk_level = RiskLevel.CRITICAL
        elif len(alerts) > 2:
            risk_level = RiskLevel.HIGH
        elif len(alerts) > 0:
            risk_level = RiskLevel.MEDIUM

        productivity = 50
        if "manpower" in brief_data:
            productivity = 75  # simplistic logic

        summary = f"Rule-based summary: Operations completed with {len(alerts)} alerts generated."
        
        return AIReviewResult(
            executive_summary=summary,
            risk_assessment=risk_level,
            key_insights=["Rule-based review executed."],
            recommendations=["Consider enabling AI provider for deeper insights."],
            anomaly_analysis="No AI analysis available.",
            safety_concerns=["Review manual safety logs."] if len(alerts) > 0 else [],
            productivity_score=productivity,
            confidence=0.5
        )

    async def _verify_with_gemini(self, brief_data: Dict[str, Any]) -> AIReviewResult:
        """
        Calls the Gemini API to verify the daily brief using google-genai.
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.warning("google-genai not installed, falling back to rule-based")
            return self._fallback_rule_based_review(brief_data)

        try:
            client = genai.Client(api_key=self.gemini_api_key)
            prompt = self._build_construction_prompt(brief_data)
            
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=AIReviewResult,
                    temperature=0.1
                )
            )
            
            result_json = response.text
            return AIReviewResult.model_validate_json(result_json)
        except Exception as e:
            logger.error(f"Gemini API verification failed: {str(e)}", exc_info=True)
            return self._fallback_rule_based_review(brief_data)

    async def _verify_with_groq(self, brief_data: Dict[str, Any]) -> AIReviewResult:
        """
        Calls the Groq API to verify the daily brief.
        """
        try:
            from groq import AsyncGroq
        except ImportError:
            logger.warning("groq not installed, falling back to rule-based")
            return self._fallback_rule_based_review(brief_data)

        try:
            client = AsyncGroq(api_key=self.groq_api_key)
            prompt = self._build_construction_prompt(brief_data)
            
            system_prompt = (
                "You are an expert AI Construction Project Manager. "
                "Output valid JSON matching the exact schema."
            )
            
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result_json = response.choices[0].message.content
            return AIReviewResult.model_validate_json(result_json)
        except Exception as e:
            logger.error(f"Groq API verification failed: {str(e)}", exc_info=True)
            return self._fallback_rule_based_review(brief_data)

    async def verify_daily_brief(self, brief_data: Dict[str, Any]) -> AIReviewResult:
        """
        Main entry point for verifying a daily brief.
        Routes to the appropriate provider based on configuration.
        """
        start_time = time.time()
        result = None
        
        if not self._is_configured() or self.provider == AIProvider.NONE:
            logger.info("AI provider not configured or set to NONE. Using rule-based fallback.")
            result = self._fallback_rule_based_review(brief_data)
        elif self.provider == AIProvider.GEMINI:
            result = await self._verify_with_gemini(brief_data)
        elif self.provider == AIProvider.GROQ:
            result = await self._verify_with_groq(brief_data)
        else:
            result = self._fallback_rule_based_review(brief_data)

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Verification completed in {latency_ms}ms")
        
        return result

def get_ai_service() -> AIVerificationService:
    """
    Module-level singleton helper for the AI verification service.
    """
    return AIVerificationService()
