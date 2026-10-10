import json
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class SubjectiveAIEvaluationOutput(BaseModel):
    score: float = Field(ge=0.0, description="Awarded marks for the answer")
    max_score: float = Field(description="Maximum marks for the question")
    correctness: float = Field(default=1.0, ge=0.0, le=1.0, description="Correctness ratio (0.0 to 1.0)")
    relevance: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance ratio (0.0 to 1.0)")
    completeness: float = Field(default=1.0, ge=0.0, le=1.0, description="Completeness ratio (0.0 to 1.0)")
    key_points_covered: List[str] = Field(default_factory=list, description="Key concepts correctly addressed")
    missing_key_points: List[str] = Field(default_factory=list, description="Important concepts omitted or incorrect")
    feedback: str = Field(default="", description="Constructive feedback for the student")
    reason: str = Field(default="", description="Justification for the awarded score")


class AISubjectiveEvaluationService:
    @staticmethod
    def _is_ai_provider_available() -> bool:
        """Checks if the Gemini API key is configured."""
        key = settings.GEMINI_API_KEY
        if not key or not key.strip() or key in ("dev_placeholder", "your_gemini_api_key_here"):
            return False
        return True

    @staticmethod
    def _get_gemini_client():
        """Returns initialized Gemini client using google.genai SDK or None if unavailable."""
        if not AISubjectiveEvaluationService._is_ai_provider_available():
            return None
        try:
            from google import genai
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client for subjective evaluation: {e}")
            return None

    def evaluate_answer(
        self,
        question_text: str,
        question_type: str,
        student_answer: Optional[str],
        model_answer: Optional[str],
        explanation: Optional[str],
        max_marks: float,
    ) -> Optional[SubjectiveAIEvaluationOutput]:
        """
        Evaluates a subjective student answer (SHORT_ANSWER, LONG_ANSWER) using Gemini AI.
        Returns SubjectiveAIEvaluationOutput or None if AI evaluation is unavailable/failed.
        Empty/whitespace student answers return score 0.0 immediately without calling Gemini API.
        """
        # 1. Check for empty or whitespace-only answer
        if not student_answer or not student_answer.strip():
            return SubjectiveAIEvaluationOutput(
                score=0.0,
                max_score=max_marks,
                correctness=0.0,
                relevance=0.0,
                completeness=0.0,
                key_points_covered=[],
                missing_key_points=["No answer submitted"],
                feedback="No answer was provided for this question.",
                reason="Unanswered subjective question."
            )

        # 2. Get Gemini client
        client = self._get_gemini_client()
        if not client:
            logger.info("Gemini AI client unavailable for subjective evaluation.")
            return None

        # 3. Construct prompt
        from google.genai import types

        prompt = f"""You are an expert academic evaluator for ExamGuard AI grading subjective examination answers.

Evaluate the following student's response based on the question specification, model answer, and grading scheme.

Question Type: {question_type}
Question Statement: {question_text}
Maximum Marks: {max_marks}
Model Answer / Key Rubric: {model_answer or 'Use standard domain knowledge for evaluation'}
Explanation / Context: {explanation or 'None'}

Student's Answer:
{student_answer.strip()}

EVALUATION INSTRUCTIONS:
1. Evaluate the response for factual correctness, accuracy, relevance, and completeness.
2. Award marks (`score`) between 0.0 and {max_marks}. DO NOT exceed {max_marks}. DO NOT return negative marks.
3. For partial credit (e.g. SHORT_ANSWER or LONG_ANSWER with partial accuracy), assign proportional marks based on key points covered.
4. List key points correctly covered in `key_points_covered`.
5. List missing or incorrect concepts in `missing_key_points`.
6. Provide concise, constructive `feedback` and a clear `reason` / justification for the score.
7. Return STRICTLY a valid JSON object matching this schema:
{{
  "score": number,
  "max_score": number,
  "correctness": number,
  "relevance": number,
  "completeness": number,
  "key_points_covered": ["string"],
  "missing_key_points": ["string"],
  "feedback": "string",
  "reason": "string"
}}
"""

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text or ""
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            # Score clamping: 0.0 <= score <= max_marks
            raw_score = float(data.get("score", 0.0))
            clamped_score = max(0.0, min(raw_score, float(max_marks)))

            out = SubjectiveAIEvaluationOutput(
                score=round(clamped_score, 2),
                max_score=float(max_marks),
                correctness=max(0.0, min(float(data.get("correctness", 1.0)), 1.0)),
                relevance=max(0.0, min(float(data.get("relevance", 1.0)), 1.0)),
                completeness=max(0.0, min(float(data.get("completeness", 1.0)), 1.0)),
                key_points_covered=[str(k) for k in data.get("key_points_covered", [])],
                missing_key_points=[str(m) for m in data.get("missing_key_points", [])],
                feedback=str(data.get("feedback", "")),
                reason=str(data.get("reason", "Evaluated by AI.")),
            )
            return out

        except Exception as e:
            logger.error(f"Error during Gemini subjective evaluation: {e}")
            return None


ai_subjective_evaluation_service = AISubjectiveEvaluationService()
