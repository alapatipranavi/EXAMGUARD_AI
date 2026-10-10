import io
import csv
import re
import uuid
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.question import QuestionType, DifficultyLevel, QuestionSource
from app.schemas.question import (
    QuestionCreate, QuestionOptionCreate,
    CSVImportParseResponse, ImportRowValidation,
    PDFImportParseResponse, PDFExtractedQuestion,
    ConfirmImportRequest, QuestionResponse
)
from app.repositories.question_repository import question_repository


class QuestionImportService:
    @staticmethod
    def _verify_examiner_role(current_user: User):
        """Ensures the authenticated user is an Examiner."""
        if current_user.role != UserRole.EXAMINER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Importing questions is restricted to Examiners."
            )

    @staticmethod
    def parse_csv(file_bytes: bytes, current_user: User) -> CSVImportParseResponse:
        """Parses CSV content and validates each row without saving to the database."""
        QuestionImportService._verify_examiner_role(current_user)

        try:
            content_str = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content_str = file_bytes.decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file encoding. Please upload a UTF-8 or Latin-1 encoded CSV file."
                )

        reader = csv.DictReader(io.StringIO(content_str))
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty or missing headers."
            )

        rows_validation: List[ImportRowValidation] = []
        valid_count = 0
        invalid_count = 0

        for row_idx, row in enumerate(reader, start=1):
            raw_data = {k.strip().lower() if k else '': (v.strip() if v else '') for k, v in row.items()}
            q_text = raw_data.get("question_text") or raw_data.get("question") or ""
            subject = raw_data.get("subject") or "General"
            topic = raw_data.get("topic") or None
            q_type_str = (raw_data.get("question_type") or raw_data.get("type") or "MCQ").upper()
            diff_str = (raw_data.get("difficulty") or "MEDIUM").upper()

            try:
                marks = float(raw_data.get("marks", 1.0))
            except ValueError:
                marks = 1.0

            try:
                neg_marks = float(raw_data.get("negative_marks", 0.0))
            except ValueError:
                neg_marks = 0.0

            model_answer = raw_data.get("model_answer") or None
            explanation = raw_data.get("explanation") or None

            # Validate Question Type
            try:
                q_type = QuestionType(q_type_str)
            except ValueError:
                rows_validation.append(ImportRowValidation(
                    row_number=row_idx,
                    is_valid=False,
                    error_message=f"Invalid question_type '{q_type_str}'. Allowed: MCQ, MULTI_SELECT, SHORT_ANSWER, LONG_ANSWER, HANDWRITTEN.",
                    raw_data=raw_data
                ))
                invalid_count += 1
                continue

            # Validate Difficulty
            try:
                difficulty = DifficultyLevel(diff_str)
            except ValueError:
                difficulty = DifficultyLevel.MEDIUM

            # Validate Text
            if not q_text.strip():
                rows_validation.append(ImportRowValidation(
                    row_number=row_idx,
                    is_valid=False,
                    error_message="Question text is empty.",
                    raw_data=raw_data
                ))
                invalid_count += 1
                continue

            # Validate Marks
            if marks <= 0:
                rows_validation.append(ImportRowValidation(
                    row_number=row_idx,
                    is_valid=False,
                    error_message="Marks must be greater than 0.",
                    raw_data=raw_data
                ))
                invalid_count += 1
                continue

            # Options parsing & validation
            options: List[QuestionOptionCreate] = []
            if q_type in (QuestionType.MCQ, QuestionType.MULTI_SELECT):
                correct_raw = (raw_data.get("correct_options") or raw_data.get("correct") or "").lower()
                correct_set = {c.strip() for c in re.split(r'[,;|]', correct_raw) if c.strip()}

                for opt_idx, key in enumerate(['option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'option_f'], start=1):
                    opt_val = raw_data.get(key)
                    if opt_val:
                        key_letter = chr(96 + opt_idx)  # 'a', 'b', 'c'...
                        is_corr = (key_letter in correct_set or str(opt_idx) in correct_set or opt_val.lower() in correct_set)
                        options.append(QuestionOptionCreate(
                            option_text=opt_val,
                            option_order=opt_idx,
                            is_correct=is_corr
                        ))

                if q_type == QuestionType.MCQ:
                    if len(options) < 2:
                        rows_validation.append(ImportRowValidation(
                            row_number=row_idx,
                            is_valid=False,
                            error_message="MCQ questions require at least 2 options (option_a, option_b...).",
                            raw_data=raw_data
                        ))
                        invalid_count += 1
                        continue
                    corr_count = sum(1 for o in options if o.is_correct)
                    if corr_count != 1:
                        rows_validation.append(ImportRowValidation(
                            row_number=row_idx,
                            is_valid=False,
                            error_message=f"MCQ questions require exactly 1 correct option (found {corr_count}). Specify in correct_options.",
                            raw_data=raw_data
                        ))
                        invalid_count += 1
                        continue

                elif q_type == QuestionType.MULTI_SELECT:
                    if len(options) < 2:
                        rows_validation.append(ImportRowValidation(
                            row_number=row_idx,
                            is_valid=False,
                            error_message="MULTI_SELECT questions require at least 2 options.",
                            raw_data=raw_data
                        ))
                        invalid_count += 1
                        continue
                    corr_count = sum(1 for o in options if o.is_correct)
                    if corr_count < 2:
                        rows_validation.append(ImportRowValidation(
                            row_number=row_idx,
                            is_valid=False,
                            error_message=f"MULTI_SELECT questions require at least 2 correct options (found {corr_count}).",
                            raw_data=raw_data
                        ))
                        invalid_count += 1
                        continue

            # Row is valid
            try:
                q_create = QuestionCreate(
                    question_text=q_text,
                    subject=subject,
                    topic=topic,
                    question_type=q_type,
                    difficulty=difficulty,
                    source=QuestionSource.CSV_IMPORT,
                    marks=marks,
                    negative_marks=neg_marks,
                    model_answer=model_answer,
                    explanation=explanation,
                    options=options if q_type in (QuestionType.MCQ, QuestionType.MULTI_SELECT) else None
                )
                rows_validation.append(ImportRowValidation(
                    row_number=row_idx,
                    is_valid=True,
                    question=q_create,
                    raw_data=raw_data
                ))
                valid_count += 1
            except Exception as val_err:
                rows_validation.append(ImportRowValidation(
                    row_number=row_idx,
                    is_valid=False,
                    error_message=str(val_err),
                    raw_data=raw_data
                ))
                invalid_count += 1

        return CSVImportParseResponse(
            total_rows=len(rows_validation),
            valid_rows_count=valid_count,
            invalid_rows_count=invalid_count,
            rows=rows_validation
        )

    @staticmethod
    def parse_pdf(file_bytes: bytes, current_user: User) -> PDFImportParseResponse:
        """Parses PDF content, extracts questions safely without fabricating answers, and returns preview items."""
        QuestionImportService._verify_examiner_role(current_user)

        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            full_text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF extraction failed: unable to read text from uploaded PDF file ({str(e)})."
            )

        if not full_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This PDF does not contain extractable text. OCR support will be added in a future stage."
            )

        # Pattern parse questions (Q1., 1., Question 1)
        raw_blocks = re.split(r'\n(?=(?:Q(?:uestion)?\s*\d+[\.\:]|\d+[\.\:]\s+[A-Z]))', full_text, flags=re.IGNORECASE)
        items: List[PDFExtractedQuestion] = []

        for idx, block in enumerate(raw_blocks, start=1):
            block_text = block.strip()
            if not block_text:
                continue

            # Extract options (A., B., C., D.)
            option_matches = re.findall(r'(?:[A-[D]]\s*[\)\.\:]\s*)([^\n]+)', block_text)
            parsed_options: List[QuestionOptionCreate] = []

            # Check if answer key is explicitly stated in block
            ans_match = re.search(r'(?:Answer|Ans|Key)[\:\=]\s*([A-D])', block_text, re.IGNORECASE)

            if option_matches:
                q_type = QuestionType.MCQ
                detected_correct_letter = ans_match.group(1).upper() if ans_match else None
                needs_review = detected_correct_letter is None

                for opt_idx, opt_txt in enumerate(option_matches, start=1):
                    letter = chr(64 + opt_idx)  # 'A', 'B', 'C'...
                    is_corr = (detected_correct_letter == letter)
                    parsed_options.append(QuestionOptionCreate(
                        option_text=opt_txt.strip(),
                        option_order=opt_idx,
                        is_correct=is_corr
                    ))
            else:
                q_type = QuestionType.SHORT_ANSWER
                needs_review = True

            # Clean question text snippet
            clean_q = re.sub(r'^(?:Q(?:uestion)?\s*\d+[\.\:]|\d+[\.\:]\s*)', '', block_text, flags=re.IGNORECASE)
            clean_q = clean_q.split("A.")[0].split("Answer:")[0].strip()

            if not clean_q:
                continue

            items.append(PDFExtractedQuestion(
                item_number=len(items) + 1,
                extracted_text=clean_q,
                detected_type=q_type,
                detected_subject="General",
                detected_difficulty=DifficultyLevel.MEDIUM,
                detected_marks=2.0,
                detected_options=parsed_options,
                detected_answer=ans_match.group(1) if ans_match else None,
                confidence_score=0.9 if ans_match else 0.6,
                needs_review=needs_review,
                is_valid=True
            ))

        return PDFImportParseResponse(
            total_extracted=len(items),
            items=items
        )

    @staticmethod
    def confirm_import(db: Session, req: ConfirmImportRequest, current_user: User) -> List[QuestionResponse]:
        """Bulk inserts confirmed examiner-reviewed questions setting appropriate source."""
        QuestionImportService._verify_examiner_role(current_user)

        if req.source not in (QuestionSource.CSV_IMPORT, QuestionSource.PDF_IMPORT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import source must be CSV_IMPORT or PDF_IMPORT."
            )

        for q in req.questions:
            q.source = req.source

        created = question_repository.bulk_create_questions(db, req.questions, current_user.id)
        return [QuestionResponse.model_validate(q) for q in created]


question_import_service = QuestionImportService()
