import uuid
import json
import logging
from typing import List, Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.user import User, UserRole
from app.models.question import QuestionType, DifficultyLevel, QuestionSource
from app.schemas.question import (
    AIGenerateRequest, AIGeneratedDraft, AIGeneratedDraftOption, AIGeneratedDraftsResponse,
    AIAssistRequest, AIAssistResponse
)

logger = logging.getLogger(__name__)


class AIQuestionService:
    @staticmethod
    def _verify_examiner_role(current_user: User):
        """Ensures the authenticated user is an Examiner."""
        if current_user.role != UserRole.EXAMINER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="AI question features are restricted to Examiners."
            )

    @staticmethod
    def _check_ai_provider_available():
        """Checks if the AI provider API key is configured. If unavailable, raises clean 503."""
        key = settings.GEMINI_API_KEY
        if not key or not key.strip() or key in ("dev_placeholder", "your_gemini_api_key_here"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is not configured. Please configure GEMINI_API_KEY."
            )

    @staticmethod
    def _get_gemini_client():
        """Returns initialized Gemini client using google.genai SDK."""
        AIQuestionService._check_ai_provider_available()
        try:
            from google import genai
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is temporarily unavailable. Please try again."
            )

    @staticmethod
    def generate_drafts(req: AIGenerateRequest, current_user: User) -> AIGeneratedDraftsResponse:
        """Generates transient question drafts via AI provider service abstraction."""
        AIQuestionService._verify_examiner_role(current_user)
        client = AIQuestionService._get_gemini_client()

        from google.genai import types

        allowed_types = [qt.value for qt in req.question_types]
        prompt = f"""You are an expert examination question author creating high-quality, pedagogically sound assessment questions for ExamGuard AI.

Generate exactly {req.count} unique, unambiguous test questions based on the following specifications:
- Subject: {req.subject}
- Topic: {req.topic}
- Allowed Question Types: {allowed_types}
- Target Difficulty: {req.difficulty.value}
- Marks per question: {req.marks}
- Learning Objective: {req.learning_objective or 'General subject proficiency'}
- Additional Instructions: {req.additional_instructions or 'None'}

CRITICAL VALIDATION CONSTRAINTS:
1. For MCQ: Must contain at least 2 options and EXACTLY 1 correct option (`is_correct: true`).
2. For MULTI_SELECT: Must contain at least 2 options and AT LEAST 2 correct options (`is_correct: true`).
3. For SHORT_ANSWER, LONG_ANSWER, HANDWRITTEN: `options` array MUST be empty `[]`.
4. `marks` must be greater than 0.
5. Provide clear, helpful `explanation` and comprehensive `model_answer` (especially for subjective questions).

Return strictly a valid JSON array of objects adhering to this schema:
[
  {{
    "question_text": "string",
    "question_type": "MCQ" | "MULTI_SELECT" | "SHORT_ANSWER" | "LONG_ANSWER" | "HANDWRITTEN",
    "difficulty": "EASY" | "MEDIUM" | "HARD",
    "marks": {req.marks},
    "negative_marks": 0.0,
    "model_answer": "string",
    "explanation": "string",
    "options": [
      {{"option_text": "string", "option_order": 1, "is_correct": true}}
    ]
  }}
]
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
            raw_items = json.loads(clean_text)

            if not isinstance(raw_items, list):
                raise ValueError("AI output is not a JSON list.")

            drafts = []
            for item in raw_items:
                q_text = str(item.get("question_text", "")).strip()
                if not q_text:
                    continue

                q_type_str = item.get("question_type", req.question_types[0].value)
                try:
                    q_type = QuestionType(q_type_str)
                except ValueError:
                    q_type = req.question_types[0]

                diff_str = item.get("difficulty", req.difficulty.value)
                try:
                    diff = DifficultyLevel(diff_str)
                except ValueError:
                    diff = req.difficulty

                q_marks = float(item.get("marks", req.marks))
                if q_marks <= 0:
                    q_marks = float(req.marks)

                neg_marks = float(item.get("negative_marks", 0.0))

                # Process options with validation
                raw_opts = item.get("options", [])
                opts = []
                if q_type in (QuestionType.MCQ, QuestionType.MULTI_SELECT):
                    if not isinstance(raw_opts, list) or len(raw_opts) < 2:
                        raise ValueError(f"Insufficient options for {q_type.value}")

                    correct_count = 0
                    for idx, o in enumerate(raw_opts):
                        o_text = str(o.get("option_text", "")).strip()
                        is_corr = bool(o.get("is_correct", False))
                        if is_corr:
                            correct_count += 1
                        opts.append(AIGeneratedDraftOption(
                            option_text=o_text,
                            option_order=idx + 1,
                            is_correct=is_corr
                        ))

                    if q_type == QuestionType.MCQ and correct_count != 1:
                        if correct_count == 0 and opts:
                            opts[0].is_correct = True
                        elif correct_count > 1:
                            first_seen = False
                            for o in opts:
                                if o.is_correct:
                                    if first_seen:
                                        o.is_correct = False
                                    else:
                                        first_seen = True
                    elif q_type == QuestionType.MULTI_SELECT and correct_count < 2:
                        needed = 2 - correct_count
                        for o in opts:
                            if not o.is_correct and needed > 0:
                                o.is_correct = True
                                needed -= 1
                else:
                    opts = []

                draft = AIGeneratedDraft(
                    draft_id=str(uuid.uuid4()),
                    question_text=q_text,
                    subject=req.subject,
                    topic=req.topic,
                    question_type=q_type,
                    difficulty=diff,
                    marks=q_marks,
                    negative_marks=neg_marks,
                    model_answer=item.get("model_answer"),
                    explanation=item.get("explanation"),
                    options=opts,
                    source=QuestionSource.AI_GENERATED
                )
                drafts.append(draft)

            if not drafts:
                raise ValueError("No valid questions parsed from AI response.")

            return AIGeneratedDraftsResponse(
                subject=req.subject,
                topic=req.topic,
                drafts=drafts
            )

        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from Gemini API.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI returned an invalid question format. Please regenerate."
            )
        except ValueError as ve:
            logger.error(f"Validation error on AI generated output: {ve}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI returned an invalid question format. Please regenerate."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini AI Provider Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is temporarily unavailable. Please try again."
            )

    @staticmethod
    def assist_question(req: AIAssistRequest, current_user: User) -> AIAssistResponse:
        """AI Assistant helper actions for manual question creation."""
        AIQuestionService._verify_examiner_role(current_user)
        client = AIQuestionService._get_gemini_client()

        from google.genai import types

        action_prompt = f"""You are an AI Question Authoring Assistant for ExamGuard AI.
Task Action: {req.action}
Current Question Statement: {req.question_text}
Question Type: {req.question_type.value}
Subject: {req.subject or 'General'}
Topic: {req.topic or 'General'}
Current Model Answer: {req.current_model_answer or 'None'}

Instructions based on Action:
- "improve" / "improve_question": Enhance clarity, academic tone, and precision of the question statement.
- "generate_options": Generate 4 distinct, plausible options. Mark correct ones according to type ({req.question_type.value}).
- "suggest_explanation": Provide a concise educational explanation for the question and answer.
- "suggest_model_answer": Generate key grading rubrics and model answer for evaluation.
- "increase_difficulty": Rephrase the question to test higher-order analytical or problem-solving skills.
- "simplify" / "simplify_language": Simplify the phrasing for clarity while preserving core concept.
- "make_application_based": Convert into a practical real-world scenario question.
- "generate_similar": Create a similar question variation on the same topic.

Return ONLY a valid JSON object matching this schema:
{{
  "improved_question_text": "string or null",
  "suggested_explanation": "string or null",
  "suggested_model_answer": "string or null",
  "suggested_options": [
    {{"option_text": "string", "option_order": 1, "is_correct": boolean}}
  ]
}}
"""
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=action_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text or ""
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            s_opts = None
            if "suggested_options" in data and isinstance(data["suggested_options"], list):
                s_opts = [
                    AIGeneratedDraftOption(
                        option_text=str(o.get("option_text", "")).strip(),
                        option_order=o.get("option_order", idx + 1),
                        is_correct=bool(o.get("is_correct", False))
                    )
                    for idx, o in enumerate(data["suggested_options"])
                    if str(o.get("option_text", "")).strip()
                ]

            return AIAssistResponse(
                action=req.action,
                improved_question_text=data.get("improved_question_text"),
                suggested_explanation=data.get("suggested_explanation"),
                suggested_model_answer=data.get("suggested_model_answer"),
                suggested_options=s_opts
            )

        except (json.JSONDecodeError, ValueError) as ve:
            logger.error(f"Parse error in AI assist response: {ve}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is temporarily unavailable. Please try again."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini AI Assistant Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is temporarily unavailable. Please try again."
            )


ai_question_service = AIQuestionService()
