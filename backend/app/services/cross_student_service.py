import uuid
import re
import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.exam import Exam
from app.models.exam_session import ExamSession, SessionStatus
from app.models.integrity import CrossStudentAnalysis
from app.models.question import Question, QuestionType
from app.schemas.cross_student import (
    CrossStudentEvidenceItem,
    CrossStudentTextMatchItem,
    CrossStudentWrongAnswerItem,
    CrossStudentPairSummaryItem,
    CrossStudentClusterStudentItem,
    CrossStudentClusterItem,
    CrossStudentPairDetailResponse,
    PaginatedCrossStudentAnalysisResponse,
)

CROSS_STUDENT_SIMILARITY_THRESHOLD = 70.0  # Threshold for High Similarity & Candidate Clusters


class CrossStudentService:
    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Normalizes text for lightweight deterministic similarity analysis."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def calculate_text_jaccard_similarity(text_a: str, text_b: str) -> float:
        """Calculates token Jaccard similarity between two text strings."""
        norm_a = CrossStudentService.normalize_text(text_a)
        norm_b = CrossStudentService.normalize_text(text_b)

        if not norm_a or not norm_b:
            return 0.0

        words_a = set(norm_a.split())
        words_b = set(norm_b.split())

        if not words_a or not words_b:
            return 0.0

        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def determine_similarity_category(self, score: float) -> str:
        """Categorizes cross-student similarity into neutral explainable buckets."""
        if score >= 70.0:
            return "HIGH_SIMILARITY"
        elif score >= 40.0:
            return "MODERATE_SIMILARITY"
        else:
            return "LOW_SIMILARITY"

    def _verify_examiner_access(self, exam: Exam, current_user: User) -> None:
        """Enforces RBAC: Examiner must own the exam, or user must be Admin."""
        if current_user.role == UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not authorized to view cross-student integrity analysis."
            )
        if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not own this exam."
            )

    def compare_session_pair(
        self, session_a: ExamSession, session_b: ExamSession, exam_questions: List[Any]
    ) -> Tuple[float, float, float, Optional[float], Optional[float], Optional[float], Dict[str, Any]]:
        """
        Calculates multi-signal deterministic similarity between two student exam sessions.
        Signals evaluated:
        1. Answer Similarity (50%)
        2. Same-Wrong-Answer Signal (15%)
        3. Timing Similarity (15%)
        4. Answer-Change Sequence Similarity (10%)
        5. Question Navigation Similarity (10%)
        """
        answers_a_map = {ans.question_id: ans for ans in session_a.answers}
        answers_b_map = {ans.question_id: ans for ans in session_b.answers}

        total_questions = len(exam_questions)
        same_correct_count = 0
        same_incorrect_count = 0
        different_answers_count = 0
        comparable_objective_count = 0

        common_wrong_answers: List[Dict[str, Any]] = []
        text_matches: List[Dict[str, Any]] = []
        objective_sim_scores: List[float] = []

        q_idx = 1
        for eq in exam_questions:
            q = eq.question
            if not q:
                continue

            qid = q.id
            ans_a = answers_a_map.get(qid)
            ans_b = answers_b_map.get(qid)

            if not ans_a or not ans_b:
                q_idx += 1
                continue

            # MCQ & MULTI_SELECT Objective comparison
            if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                opts_a = set(so.option_id for so in ans_a.selected_options) if ans_a.selected_options else set()
                opts_b = set(so.option_id for so in ans_b.selected_options) if ans_b.selected_options else set()

                correct_opts = set(opt.id for opt in q.options if opt.is_correct)

                if opts_a or opts_b:
                    comparable_objective_count += 1

                    if opts_a == opts_b:
                        objective_sim_scores.append(1.0)
                        if opts_a == correct_opts:
                            same_correct_count += 1
                        else:
                            same_incorrect_count += 1
                            # Format common wrong answer evidence
                            sel_a_text = ", ".join(opt.option_text for opt in q.options if opt.id in opts_a) or "None"
                            corr_text = ", ".join(opt.option_text for opt in q.options if opt.is_correct) or "None"
                            common_wrong_answers.append({
                                "question_id": str(qid),
                                "question_number": q_idx,
                                "question_text": q.question_text,
                                "student_a_option": sel_a_text,
                                "student_b_option": sel_a_text,
                                "correct_option": corr_text,
                            })
                    else:
                        different_answers_count += 1
                        if opts_a and opts_b:
                            jaccard = len(opts_a.intersection(opts_b)) / len(opts_a.union(opts_b))
                            objective_sim_scores.append(jaccard)
                        else:
                            objective_sim_scores.append(0.0)

            # SHORT & LONG Subjective Text comparison
            elif q.question_type in [QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER]:
                txt_a = ans_a.text_answer or ""
                txt_b = ans_b.text_answer or ""
                if txt_a and txt_b:
                    j_sim = self.calculate_text_jaccard_similarity(txt_a, txt_b)
                    if j_sim > 0.40:
                        text_matches.append({
                            "question_id": str(qid),
                            "question_number": q_idx,
                            "question_text": q.question_text,
                            "student_a_text": txt_a,
                            "student_b_text": txt_b,
                            "similarity_score": round(j_sim * 100, 2),
                        })

            q_idx += 1

        # Calculate Answer Similarity (0 - 1)
        answer_corr = (sum(objective_sim_scores) / len(objective_sim_scores)) if objective_sim_scores else 0.0

        # Calculate Same-Wrong-Answer Signal (0 - 1)
        wrong_answer_corr = (
            (same_incorrect_count / comparable_objective_count) if comparable_objective_count > 0 else 0.0
        )

        # 3. Timing Similarity from Session Metadata & Events
        timing_corr: Optional[float] = None
        per_question_timing: List[Dict[str, Any]] = []

        meta_a = session_a.session_metadata or {}
        meta_b = session_b.session_metadata or {}
        timing_a_dict = meta_a.get("question_durations", {})
        timing_b_dict = meta_b.get("question_durations", {})

        timing_sims: List[float] = []
        if timing_a_dict and timing_b_dict:
            for qid_str, time_a in timing_a_dict.items():
                if qid_str in timing_b_dict:
                    t_a = float(time_a)
                    t_b = float(timing_b_dict[qid_str])
                    max_t = max(t_a, t_b)
                    if max_t > 0:
                        t_sim = 1.0 - (abs(t_a - t_b) / max_t)
                        timing_sims.append(max(0.0, min(1.0, t_sim)))
                        per_question_timing.append({
                            "question_id": qid_str,
                            "time_a_seconds": round(t_a, 1),
                            "time_b_seconds": round(t_b, 1),
                            "similarity": round(t_sim * 100, 1),
                        })

        if timing_sims:
            timing_corr = sum(timing_sims) / len(timing_sims)

        # 4. Answer-Change Sequence Similarity
        change_corr: Optional[float] = None
        answer_change_sequences: List[Dict[str, Any]] = []

        changes_a = meta_a.get("answer_changes", {})
        changes_b = meta_b.get("answer_changes", {})

        matching_changes_count = 0
        total_change_qs = 0
        if changes_a and changes_b:
            for qid_str, seq_a in changes_a.items():
                if qid_str in changes_b:
                    total_change_qs += 1
                    seq_b = changes_b[qid_str]
                    if seq_a == seq_b:
                        matching_changes_count += 1
                        answer_change_sequences.append({
                            "question_id": qid_str,
                            "sequence_a": seq_a,
                            "sequence_b": seq_b,
                            "matched": True,
                        })

        if total_change_qs > 0:
            change_corr = matching_changes_count / total_change_qs

        # 5. Question Navigation Sequence Similarity
        nav_corr: Optional[float] = None
        navigation_sequences: List[Dict[str, Any]] = []

        nav_a = meta_a.get("navigation_order", [])
        nav_b = meta_b.get("navigation_order", [])

        if nav_a and nav_b:
            j_nav = len(set(nav_a).intersection(set(nav_b))) / len(set(nav_a).union(set(nav_b)))
            nav_corr = j_nav
            navigation_sequences.append({
                "nav_a": nav_a,
                "nav_b": nav_b,
                "jaccard_similarity": round(j_nav * 100, 1),
            })

        # Calculate Weighted Combined Score (0 - 100)
        weights = [
            (answer_corr, 0.50),
            (wrong_answer_corr, 0.15),
            (timing_corr, 0.15),
            (change_corr, 0.10),
            (nav_corr, 0.10),
        ]

        active_weighted_sum = 0.0
        active_weight_total = 0.0

        for val, w in weights:
            if val is not None:
                active_weighted_sum += val * w
                active_weight_total += w

        if active_weight_total > 0:
            combined_ratio = active_weighted_sum / active_weight_total
        else:
            combined_ratio = answer_corr

        similarity_score = round(combined_ratio * 100, 2)

        # Generate Human-Readable Evidence Items
        evidence_items: List[str] = []
        if comparable_objective_count > 0:
            matched_obj = same_correct_count + same_incorrect_count
            evidence_items.append(
                f"{matched_obj} of {comparable_objective_count} objective answers matched between both students."
            )

        if same_incorrect_count > 0:
            evidence_items.append(
                f"{same_incorrect_count} identical incorrect option selection(s) detected across comparable questions."
            )

        if text_matches:
            evidence_items.append(
                f"{len(text_matches)} subjective answer(s) demonstrated high textual similarity."
            )

        if timing_corr is not None and timing_corr >= 0.70:
            evidence_items.append(
                f"Question attempt timing was highly correlated ({int(timing_corr * 100)}% timing similarity)."
            )

        if change_corr is not None and change_corr >= 0.70:
            evidence_items.append(
                f"Answer-change sequences matched on {matching_changes_count} question(s)."
            )

        if nav_corr is not None and nav_corr >= 0.70:
            evidence_items.append(
                f"Question navigation pattern matched ({int(nav_corr * 100)}% navigation similarity)."
            )

        if not evidence_items:
            evidence_items.append("Standard response patterns observed across both student sessions.")

        metadata_dict = {
            "evidence_items": evidence_items,
            "same_incorrect_answers_count": same_incorrect_count,
            "same_correct_answers_count": same_correct_count,
            "total_comparable_questions": comparable_objective_count,
            "common_wrong_answers": common_wrong_answers,
            "text_matches": text_matches,
            "per_question_timing": per_question_timing,
            "answer_change_sequences": answer_change_sequences,
            "navigation_sequences": navigation_sequences,
        }

        return (
            similarity_score,
            round(answer_corr, 2),
            round(wrong_answer_corr, 2),
            round(timing_corr, 2) if timing_corr is not None else None,
            round(change_corr, 2) if change_corr is not None else None,
            round(nav_corr, 2) if nav_corr is not None else None,
            metadata_dict,
        )

    def _generate_candidate_clusters(
        self, sessions_map: Dict[uuid.UUID, ExamSession], analysis_records: List[CrossStudentAnalysis]
    ) -> Dict[uuid.UUID, str]:
        """
        Builds graph-based candidate similarity clusters where similarity >= 70%.
        Returns mapping of session_id -> cluster_id string (e.g. 'Cluster 1').
        """
        adj: Dict[uuid.UUID, Set[uuid.UUID]] = {sid: set() for sid in sessions_map.keys()}

        for rec in analysis_records:
            if float(rec.similarity_score) >= CROSS_STUDENT_SIMILARITY_THRESHOLD:
                adj[rec.source_session_id].add(rec.target_session_id)
                adj[rec.target_session_id].add(rec.source_session_id)

        visited: Set[uuid.UUID] = set()
        cluster_assignments: Dict[uuid.UUID, str] = {}
        cluster_num = 1

        for sid in sessions_map.keys():
            if sid not in visited and adj[sid]:
                component: List[uuid.UUID] = []
                queue = [sid]
                visited.add(sid)

                while queue:
                    curr = queue.pop(0)
                    component.append(curr)
                    for nbr in adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)

                if len(component) >= 2:
                    c_name = f"Cluster {cluster_num}"
                    for member in component:
                        cluster_assignments[member] = c_name
                    cluster_num += 1

        return cluster_assignments

    def run_analysis_for_exam(
        self, db: Session, exam_id: uuid.UUID, current_user: User
    ) -> Dict[str, Any]:
        """
        Calculates pairwise cross-student integrity similarity for all submitted sessions of an exam.
        Idempotent: Replaces previous analysis for the target exam safely.
        """
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._verify_examiner_access(exam, current_user)

        # 1. Fetch submitted / completed sessions only
        eligible_statuses = [
            SessionStatus.SUBMITTED,
            SessionStatus.AUTO_SUBMITTED,
            SessionStatus.EXPIRED,
            SessionStatus.TERMINATED,
        ]
        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.exam_id == exam_id, ExamSession.status.in_(eligible_statuses))
            .all()
        )

        if len(sessions) < 2:
            # Clean empty state: Not enough student attempts
            db.query(CrossStudentAnalysis).filter(CrossStudentAnalysis.exam_id == exam_id).delete()
            db.commit()
            return {
                "message": "Not enough student attempts for cross-student analysis.",
                "analyzed_students_count": len(sessions),
                "total_pairs_count": 0,
            }

        # 2. Clear previous analysis records for this exam
        db.query(CrossStudentAnalysis).filter(CrossStudentAnalysis.exam_id == exam_id).delete()
        db.commit()

        # Sort sessions deterministically by session ID string
        sessions.sort(key=lambda s: str(s.id))
        sessions_map = {s.id: s for s in sessions}
        exam_questions = list(exam.exam_questions)
        exam_questions.sort(key=lambda x: x.question_order)

        analysis_records: List[CrossStudentAnalysis] = []

        # 3. Compute Pairwise Similarity (Normalized source < target)
        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                sess_a = sessions[i]
                sess_b = sessions[j]

                # Guarantee source_session_id < target_session_id
                if str(sess_a.id) > str(sess_b.id):
                    source_sess, target_sess = sess_b, sess_a
                else:
                    source_sess, target_sess = sess_a, sess_b

                sim_score, ans_corr, wrong_corr, tim_corr, chg_corr, nav_corr, meta = self.compare_session_pair(
                    source_sess, target_sess, exam_questions
                )

                rec = CrossStudentAnalysis(
                    id=uuid.uuid4(),
                    exam_id=exam_id,
                    source_session_id=source_sess.id,
                    target_session_id=target_sess.id,
                    similarity_score=sim_score,
                    answer_correlation=ans_corr,
                    timing_correlation=tim_corr,
                    behaviour_correlation=chg_corr,
                    overall_confidence=1.0,
                    analysis_metadata=meta,
                    created_at=datetime.now(timezone.utc),
                )
                analysis_records.append(rec)
                db.add(rec)

        db.commit()

        # 4. Generate Candidate Clusters
        cluster_assignments = self._generate_candidate_clusters(sessions_map, analysis_records)

        if cluster_assignments:
            for rec in analysis_records:
                src_c = cluster_assignments.get(rec.source_session_id)
                tgt_c = cluster_assignments.get(rec.target_session_id)
                if src_c and src_c == tgt_c:
                    meta = dict(rec.analysis_metadata or {})
                    meta["cluster_id"] = src_c
                    rec.analysis_metadata = meta
            db.commit()

        return {
            "message": "Cross-student integrity analysis completed successfully.",
            "analyzed_students_count": len(sessions),
            "total_pairs_count": len(analysis_records),
        }

    def get_analysis_summary(
        self,
        db: Session,
        exam_id: uuid.UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        min_similarity: Optional[float] = None,
        cluster_id: Optional[str] = None,
    ) -> PaginatedCrossStudentAnalysisResponse:
        """Returns aggregated exam-level cross-student similarity analysis summary, clusters, and pairwise table."""
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._verify_examiner_access(exam, current_user)

        records = (
            db.query(CrossStudentAnalysis)
            .filter(CrossStudentAnalysis.exam_id == exam_id)
            .order_by(CrossStudentAnalysis.similarity_score.desc())
            .all()
        )

        # Collect unique student sessions
        session_ids: Set[uuid.UUID] = set()
        for r in records:
            session_ids.add(r.source_session_id)
            session_ids.add(r.target_session_id)

        session_map: Dict[uuid.UUID, ExamSession] = {}
        if session_ids:
            s_list = db.query(ExamSession).filter(ExamSession.id.in_(session_ids)).all()
            session_map = {s.id: s for s in s_list}

        high_count = sum(1 for r in records if float(r.similarity_score) >= 70.0)
        mod_count = sum(1 for r in records if 40.0 <= float(r.similarity_score) < 70.0)
        low_count = sum(1 for r in records if float(r.similarity_score) < 40.0)

        last_analyzed_at = records[0].created_at if records else None

        # Build Clusters Summary
        cluster_groups: Dict[str, List[CrossStudentAnalysis]] = {}
        for r in records:
            meta = r.analysis_metadata or {}
            c_id = meta.get("cluster_id")
            if c_id:
                if c_id not in cluster_groups:
                    cluster_groups[c_id] = []
                cluster_groups[c_id].append(r)

        clusters_list: List[CrossStudentClusterItem] = []
        for c_id, c_records in cluster_groups.items():
            c_sids: Set[uuid.UUID] = set()
            sim_sum = 0.0
            ev_summary_set: Set[str] = set()

            for cr in c_records:
                c_sids.add(cr.source_session_id)
                c_sids.add(cr.target_session_id)
                sim_sum += float(cr.similarity_score)
                meta = cr.analysis_metadata or {}
                for ev in meta.get("evidence_items", []):
                    ev_summary_set.add(ev)

            stud_items: List[CrossStudentClusterStudentItem] = []
            for sid in c_sids:
                s_obj = session_map.get(sid)
                if s_obj and s_obj.student:
                    stud_items.append(
                        CrossStudentClusterStudentItem(
                            student_id=s_obj.student_id,
                            student_name=f"{s_obj.student.first_name} {s_obj.student.last_name}",
                            student_email=s_obj.student.email,
                            session_id=sid,
                        )
                    )

            avg_sim = round(sim_sum / len(c_records), 2) if c_records else 0.0
            clusters_list.append(
                CrossStudentClusterItem(
                    cluster_id=c_id,
                    student_count=len(stud_items),
                    average_similarity=avg_sim,
                    students=stud_items,
                    key_evidence=list(ev_summary_set)[:4],
                )
            )

        # Filter Records for Pairwise Table
        filtered_records = records
        if min_similarity is not None:
            filtered_records = [r for r in filtered_records if float(r.similarity_score) >= min_similarity]
        if cluster_id:
            filtered_records = [
                r for r in filtered_records if (r.analysis_metadata or {}).get("cluster_id") == cluster_id
            ]

        total = len(filtered_records)
        pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size
        paged_records = filtered_records[offset : offset + page_size]

        summary_items: List[CrossStudentPairSummaryItem] = []
        for r in paged_records:
            s_src = session_map.get(r.source_session_id)
            s_tgt = session_map.get(r.target_session_id)

            src_name = f"{s_src.student.first_name} {s_src.student.last_name}" if s_src and s_src.student else "Student A"
            src_email = s_src.student.email if s_src and s_src.student else ""
            src_id = s_src.student_id if s_src else r.source_session_id

            tgt_name = f"{s_tgt.student.first_name} {s_tgt.student.last_name}" if s_tgt and s_tgt.student else "Student B"
            tgt_email = s_tgt.student.email if s_tgt and s_tgt.student else ""
            tgt_id = s_tgt.student_id if s_tgt else r.target_session_id

            score = float(r.similarity_score)
            cat = self.determine_similarity_category(score)
            meta = r.analysis_metadata or {}

            summary_items.append(
                CrossStudentPairSummaryItem(
                    id=r.id,
                    exam_id=exam_id,
                    source_session_id=r.source_session_id,
                    target_session_id=r.target_session_id,
                    source_student_id=src_id,
                    source_student_name=src_name,
                    source_student_email=src_email,
                    target_student_id=tgt_id,
                    target_student_name=tgt_name,
                    target_student_email=tgt_email,
                    similarity_score=score,
                    answer_similarity=float(r.answer_correlation or 0.0) * 100,
                    wrong_answer_similarity=round(
                        (meta.get("same_incorrect_answers_count", 0) / max(1, meta.get("total_comparable_questions", 1))) * 100, 2
                    ),
                    timing_similarity=float(r.timing_correlation * 100) if r.timing_correlation is not None else None,
                    answer_change_similarity=float(r.behaviour_correlation * 100) if r.behaviour_correlation is not None else None,
                    navigation_similarity=None,
                    same_incorrect_answers_count=meta.get("same_incorrect_answers_count", 0),
                    same_correct_answers_count=meta.get("same_correct_answers_count", 0),
                    category=cat,
                    cluster_id=meta.get("cluster_id"),
                )
            )

        return PaginatedCrossStudentAnalysisResponse(
            exam_id=exam.id,
            exam_title=exam.title,
            analyzed_students_count=len(session_ids),
            total_pairs_count=len(records),
            high_similarity_pairs_count=high_count,
            moderate_similarity_pairs_count=mod_count,
            low_similarity_pairs_count=low_count,
            last_analyzed_at=last_analyzed_at,
            clusters=clusters_list,
            items=summary_items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def get_pair_detail(
        self, db: Session, exam_id: uuid.UUID, analysis_id: uuid.UUID, current_user: User
    ) -> CrossStudentPairDetailResponse:
        """Returns detailed explainable evidence for a single pairwise cross-student similarity record."""
        rec = (
            db.query(CrossStudentAnalysis)
            .filter(CrossStudentAnalysis.id == analysis_id, CrossStudentAnalysis.exam_id == exam_id)
            .first()
        )
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cross-student analysis record not found.")

        exam = rec.exam
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._verify_examiner_access(exam, current_user)

        s_src = db.query(ExamSession).filter(ExamSession.id == rec.source_session_id).first()
        s_tgt = db.query(ExamSession).filter(ExamSession.id == rec.target_session_id).first()

        src_name = f"{s_src.student.first_name} {s_src.student.last_name}" if s_src and s_src.student else "Student A"
        src_email = s_src.student.email if s_src and s_src.student else ""
        src_id = s_src.student_id if s_src else rec.source_session_id

        tgt_name = f"{s_tgt.student.first_name} {s_tgt.student.last_name}" if s_tgt and s_tgt.student else "Student B"
        tgt_email = s_tgt.student.email if s_tgt and s_tgt.student else ""
        tgt_id = s_tgt.student_id if s_tgt else rec.target_session_id

        score = float(rec.similarity_score)
        cat = self.determine_similarity_category(score)
        meta = rec.analysis_metadata or {}

        wrong_answers = meta.get("common_wrong_answers", [])
        text_matches = meta.get("text_matches", [])

        return CrossStudentPairDetailResponse(
            id=rec.id,
            exam_id=exam_id,
            exam_title=exam.title,
            source_session_id=rec.source_session_id,
            target_session_id=rec.target_session_id,
            source_student_id=src_id,
            source_student_name=src_name,
            source_student_email=src_email,
            target_student_id=tgt_id,
            target_student_name=tgt_name,
            target_student_email=tgt_email,
            similarity_score=score,
            category=cat,
            answer_similarity=float(rec.answer_correlation or 0.0) * 100,
            wrong_answer_similarity=round(
                (meta.get("same_incorrect_answers_count", 0) / max(1, meta.get("total_comparable_questions", 1))) * 100, 2
            ),
            timing_similarity=float(rec.timing_correlation * 100) if rec.timing_correlation is not None else None,
            answer_change_similarity=float(rec.behaviour_correlation * 100) if rec.behaviour_correlation is not None else None,
            navigation_similarity=None,
            same_incorrect_answers_count=meta.get("same_incorrect_answers_count", 0),
            same_correct_answers_count=meta.get("same_correct_answers_count", 0),
            total_comparable_questions=meta.get("total_comparable_questions", 0),
            evidence_items=meta.get("evidence_items", []),
            common_wrong_answers=wrong_answers,
            text_matches=text_matches,
            per_question_timing=meta.get("per_question_timing", []),
            answer_change_sequences=meta.get("answer_change_sequences", []),
            navigation_sequences=meta.get("navigation_sequences", []),
            generated_at=rec.created_at,
        )


cross_student_service = CrossStudentService()
