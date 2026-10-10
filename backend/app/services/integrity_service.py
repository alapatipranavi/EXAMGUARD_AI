import uuid
import math
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.exam import Exam
from app.models.exam_session import ExamSession, SessionStatus
from app.models.proctoring import ProctoringEvent, ProctoringEventType, EventSeverity
from app.models.integrity import IntegrityAnalysis, AnalysisStatus
from app.schemas.integrity import (
    IntegrityEvidenceItem,
    IntegrityTimelineItem,
    IntegritySignalsSummary,
    SessionIntegrityDetailResponse,
    ExamIntegritySummaryItem,
    PaginatedExamIntegrityResponse,
)
from app.schemas.student_integrity import (
    StudentIntegritySummary,
    StudentExamIntegrityItem,
    StudentIntegrityOverviewResponse,
    StudentProctoringEventItem,
    StudentBehaviouralMetrics,
    StudentEnvironmentMonitoring,
    StudentSessionIntegrityDetailResponse,
)

# Centralized Scoring Configuration & Thresholds
BASELINE_INTEGRITY_SCORE = 100.0

DEDUCTIONS_CONFIG = {
    "TAB_SWITCH": {"per_event": 5.0, "max_deduction": 30.0, "title": "Tab Switch Events"},
    "FULLSCREEN_EXITED": {"per_event": 7.0, "max_deduction": 28.0, "title": "Fullscreen Exit Events"},
    "FACE_NOT_DETECTED": {"per_event": 6.0, "max_deduction": 30.0, "title": "Face Absence Events"},
    "MULTIPLE_FACES_DETECTED": {"per_event": 10.0, "max_deduction": 30.0, "title": "Multiple Face Detection"},
    "CAMERA_DISCONNECTED": {"per_event": 12.0, "max_deduction": 24.0, "title": "Camera Disconnection"},
    "MICROPHONE_DISCONNECTED": {"per_event": 8.0, "max_deduction": 16.0, "title": "Microphone Disconnection"},
    "TAB_SWITCH_LIMIT_EXCEEDED": {"per_event": 20.0, "max_deduction": 20.0, "title": "Tab Switch Limit Violation"},
    "AUTO_SUBMITTED_STATUS": {"per_event": 15.0, "max_deduction": 15.0, "title": "Automated Session Termination"},
    "PHONE_DETECTED": {"per_event": 8.0, "max_deduction": 24.0, "title": "Mobile Phone Detection"},
    "LAPTOP_DETECTED": {"per_event": 6.0, "max_deduction": 18.0, "title": "Additional Device Detection"},
    "BOOK_DETECTED": {"per_event": 5.0, "max_deduction": 15.0, "title": "Book / Notes Detection"},
    "ADDITIONAL_PERSON_DETECTED": {"per_event": 10.0, "max_deduction": 30.0, "title": "Additional Person Presence"},
    "RAPID_ANSWER_CHANGES": {"per_event": 2.0, "max_deduction": 8.0, "title": "Rapid Answer Changes"},
    "UNUSUAL_TIMING": {"per_event": 3.0, "max_deduction": 9.0, "title": "Unusual Answer Timing"},
    "NAVIGATION_ANOMALY": {"per_event": 2.0, "max_deduction": 6.0, "title": "Navigation Pattern Anomaly"},
    "BEHAVIOURAL_ANOMALY": {"per_event": 5.0, "max_deduction": 10.0, "title": "Combined Behavioural Anomaly"},
    "IDENTITY_MISMATCH_CONFIRMED": {"per_event": 10.0, "max_deduction": 10.0, "title": "Identity Verification Mismatch"},
}

RISK_THRESHOLDS = {
    "LOW_MIN_SCORE": 85.0,      # Score >= 85 -> LOW Risk
    "MODERATE_MIN_SCORE": 65.0, # 65 <= Score < 85 -> MODERATE Risk
}


class IntegrityService:
    def determine_risk_level(self, score: float) -> str:
        """Determines neutral risk level from integrity score."""
        if score >= RISK_THRESHOLDS["LOW_MIN_SCORE"]:
            return "LOW"
        elif score >= RISK_THRESHOLDS["MODERATE_MIN_SCORE"]:
            return "MODERATE"
        else:
            return "HIGH"

    def determine_recommendation(self, risk_level: str) -> str:
        """Generates neutral examiner recommendation based on risk level."""
        if risk_level == "LOW":
            return "Normal session activity observed. No examiner action required."
        elif risk_level == "MODERATE":
            return "Minor session anomalies detected. Examiner review optional."
        else:
            return "Examiner review recommended based on multiple observed integrity signals."

    def calculate_session_integrity(
        self, session: ExamSession, proctoring_events: List[ProctoringEvent]
    ) -> Tuple[float, str, str, List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int], Dict[str, Any]]:
        """
        Calculates deterministic integrity score, evidence items, chronological timeline,
        summary signals dictionary, and Stage 9.3 behavioural fingerprint.
        """
        score = BASELINE_INTEGRITY_SCORE
        evidence_items: List[Dict[str, Any]] = []

        # Count event types
        event_counts: Dict[str, int] = {
            "tab_switches": 0,
            "fullscreen_exits": 0,
            "face_not_detected": 0,
            "multiple_faces": 0,
            "camera_issues": 0,
            "microphone_issues": 0,
            "tab_limit_exceeded": 0,
        }

        # Stage 9.3 Behavioural Event Collections
        q_views: List[Tuple[datetime, str]] = []
        ans_changes: List[Tuple[datetime, str]] = []
        ans_clears: List[Tuple[datetime, str]] = []
        navigations: List[Tuple[datetime, str, str]] = []

        rapid_change_events_count = 0
        unusual_timing_events_count = 0
        nav_anomaly_events_count = 0
        behavioural_anomaly_events_count = 0

        for ev in proctoring_events:
            ev_type_str = str(ev.event_type.value) if hasattr(ev.event_type, "value") else str(ev.event_type)
            ts = ev.occurred_at or session.created_at
            meta = ev.event_metadata or {}

            if ev_type_str in ["TAB_HIDDEN", "TAB_SWITCH", "WINDOW_BLUR"]:
                event_counts["tab_switches"] += 1
            elif ev_type_str == "FULLSCREEN_EXITED":
                event_counts["fullscreen_exits"] += 1
            elif ev_type_str in ["FACE_NOT_DETECTED", "FACE_MISSING"]:
                event_counts["face_not_detected"] += 1
            elif ev_type_str in ["MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"]:
                event_counts["multiple_faces"] += 1
            elif ev_type_str in ["CAMERA_DISCONNECTED", "CAMERA_PERMISSION_DENIED", "CAMERA_ISSUE"]:
                event_counts["camera_issues"] += 1
            elif ev_type_str in ["MICROPHONE_DISCONNECTED", "MICROPHONE_PERMISSION_DENIED"]:
                event_counts["microphone_issues"] += 1
            elif ev_type_str == "TAB_SWITCH_LIMIT_EXCEEDED":
                event_counts["tab_limit_exceeded"] += 1
            elif ev_type_str == "PHONE_DETECTED":
                event_counts["phone_detected"] = event_counts.get("phone_detected", 0) + 1
            elif ev_type_str == "LAPTOP_DETECTED":
                event_counts["laptop_detected"] = event_counts.get("laptop_detected", 0) + 1
            elif ev_type_str == "BOOK_DETECTED":
                event_counts["book_detected"] = event_counts.get("book_detected", 0) + 1
            elif ev_type_str == "ADDITIONAL_PERSON_DETECTED":
                event_counts["additional_person"] = event_counts.get("additional_person", 0) + 1
            elif ev_type_str == "QUESTION_VIEWED":
                q_id = meta.get("question_id", "")
                if q_id:
                    q_views.append((ts, q_id))
            elif ev_type_str in ["ANSWER_CREATED", "ANSWER_CHANGED"]:
                q_id = meta.get("question_id", "")
                if q_id:
                    ans_changes.append((ts, q_id))
            elif ev_type_str == "ANSWER_CLEARED":
                q_id = meta.get("question_id", "")
                if q_id:
                    ans_clears.append((ts, q_id))
            elif ev_type_str == "QUESTION_NAVIGATION":
                from_q = meta.get("from_question_id", "")
                to_q = meta.get("to_question_id", "")
                if from_q and to_q:
                    navigations.append((ts, from_q, to_q))
            elif ev_type_str == "RAPID_ANSWER_CHANGES":
                rapid_change_events_count += 1
            elif ev_type_str == "UNUSUAL_TIMING":
                unusual_timing_events_count += 1
            elif ev_type_str == "NAVIGATION_ANOMALY":
                nav_anomaly_events_count += 1
            elif ev_type_str == "BEHAVIOURAL_ANOMALY":
                behavioural_anomaly_events_count += 1

        # ----------------------------------------------------
        # Stage 9.3 Pattern Analysis & Behavioural Fingerprint
        # ----------------------------------------------------
        # 1. Rapid Answer Modification Clusters (3+ changes/clears within 5.0s)
        all_modifications = sorted(ans_changes + ans_clears, key=lambda x: x[0] if x[0] else datetime.min)
        rapid_change_clusters = 0
        if len(all_modifications) >= 3:
            for i in range(len(all_modifications) - 2):
                t1 = all_modifications[i][0]
                t3 = all_modifications[i + 2][0]
                if t1 and t3:
                    delta = (t3 - t1).total_seconds()
                    if 0 <= delta <= 5.0:
                        rapid_change_clusters += 1

        # 2. Timing Analysis (Question View Intervals)
        sorted_views = sorted(q_views, key=lambda x: x[0] if x[0] else datetime.min)
        question_durations: List[float] = []
        very_fast_count = 0

        for i in range(len(sorted_views) - 1):
            t_curr = sorted_views[i][0]
            t_next = sorted_views[i + 1][0]
            if t_curr and t_next:
                dur = (t_next - t_curr).total_seconds()
                if 0.5 <= dur <= 3600.0:
                    question_durations.append(dur)
                    if dur < 3.0:
                        very_fast_count += 1

        avg_q_time = round(sum(question_durations) / len(question_durations), 1) if question_durations else 0.0
        sorted_durs = sorted(question_durations)
        median_q_time = round(sorted_durs[len(sorted_durs) // 2], 1) if sorted_durs else 0.0

        # 3. Navigation & Backtracking Analysis
        visited_questions: set = set()
        backtrack_count = 0
        for nav in navigations:
            from_q, to_q = nav[1], nav[2]
            if to_q in visited_questions:
                backtrack_count += 1
            visited_questions.add(from_q)
            visited_questions.add(to_q)

        for qv in q_views:
            visited_questions.add(qv[1])

        behavioural_summary = {
            "questions_visited": len(visited_questions),
            "questions_answered": len(session.answers or []),
            "answer_change_count": len(ans_changes),
            "clear_count": len(ans_clears),
            "navigation_count": len(navigations),
            "backtrack_count": backtrack_count,
            "average_question_time": avg_q_time,
            "median_question_time": median_q_time,
            "very_fast_answer_count": very_fast_count,
            "rapid_change_count": max(rapid_change_clusters, rapid_change_events_count),
        }

        # Calculate deductions
        # 1. Tab switches
        if event_counts["tab_switches"] > 0:
            cfg = DEDUCTIONS_CONFIG["TAB_SWITCH"]
            deduction = min(event_counts["tab_switches"] * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "TAB_SWITCH",
                "title": cfg["title"],
                "count": event_counts["tab_switches"],
                "severity": "WARNING" if event_counts["tab_switches"] > 2 else "MEDIUM",
                "observation": f"Multiple visibility changes ({event_counts['tab_switches']}) were detected during the examination.",
                "score_deduction": round(deduction, 2),
            })

        # 2. Fullscreen exits
        if event_counts["fullscreen_exits"] > 0:
            cfg = DEDUCTIONS_CONFIG["FULLSCREEN_EXITED"]
            deduction = min(event_counts["fullscreen_exits"] * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "FULLSCREEN_EXITED",
                "title": cfg["title"],
                "count": event_counts["fullscreen_exits"],
                "severity": "WARNING",
                "observation": f"Student exited full-screen mode {event_counts['fullscreen_exits']} time(s).",
                "score_deduction": round(deduction, 2),
            })

        # 3. Face absence
        if event_counts["face_not_detected"] > 0:
            cfg = DEDUCTIONS_CONFIG["FACE_NOT_DETECTED"]
            deduction = min(event_counts["face_not_detected"] * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "FACE_NOT_DETECTED",
                "title": cfg["title"],
                "count": event_counts["face_not_detected"],
                "severity": "HIGH" if event_counts["face_not_detected"] > 3 else "MEDIUM",
                "observation": f"Face presence was unavailable during {event_counts['face_not_detected']} monitoring interval(s).",
                "score_deduction": round(deduction, 2),
            })

        # 4. Multiple faces
        if event_counts["multiple_faces"] > 0:
            cfg = DEDUCTIONS_CONFIG["MULTIPLE_FACES_DETECTED"]
            deduction = min(event_counts["multiple_faces"] * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "MULTIPLE_FACES_DETECTED",
                "title": cfg["title"],
                "count": event_counts["multiple_faces"],
                "severity": "HIGH",
                "observation": f"Multiple faces were observed in frame across {event_counts['multiple_faces']} monitoring interval(s).",
                "score_deduction": round(deduction, 2),
            })

        # 5. Camera disconnects
        if event_counts["camera_issues"] > 0:
            cfg = DEDUCTIONS_CONFIG["CAMERA_DISCONNECTED"]
            deduction = min(event_counts["camera_issues"] * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "CAMERA_DISCONNECTED",
                "title": cfg["title"],
                "count": event_counts["camera_issues"],
                "severity": "CRITICAL",
                "observation": f"Camera hardware or permission interruption occurred ({event_counts['camera_issues']} event(s)).",
                "score_deduction": round(deduction, 2),
            })

        # 6. Microphone disconnects
        if event_counts["microphone_issues"] > 0:
            cfg = DEDUCTIONS_CONFIG["MICROPHONE_DISCONNECTED"]
            deduction = min(event_counts["microphone_issues"] * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "MICROPHONE_DISCONNECTED",
                "title": cfg["title"],
                "count": event_counts["microphone_issues"],
                "severity": "HIGH",
                "observation": f"Microphone stream interruption detected ({event_counts['microphone_issues']} event(s)).",
                "score_deduction": round(deduction, 2),
            })

        # 7. Tab limit exceeded
        if event_counts["tab_limit_exceeded"] > 0:
            cfg = DEDUCTIONS_CONFIG["TAB_SWITCH_LIMIT_EXCEEDED"]
            deduction = cfg["per_event"]
            score -= deduction
            evidence_items.append({
                "signal_type": "TAB_SWITCH_LIMIT_EXCEEDED",
                "title": cfg["title"],
                "count": event_counts["tab_limit_exceeded"],
                "severity": "CRITICAL",
                "observation": "Allowed tab-switch limit was exceeded, triggering system session lock.",
                "score_deduction": round(deduction, 2),
            })

        # 8. Auto-submitted status
        if session.status in [SessionStatus.AUTO_SUBMITTED, SessionStatus.TERMINATED]:
            cfg = DEDUCTIONS_CONFIG["AUTO_SUBMITTED_STATUS"]
            deduction = cfg["per_event"]
            score -= deduction
            evidence_items.append({
                "signal_type": "AUTO_SUBMITTED_STATUS",
                "title": cfg["title"],
                "count": 1,
                "severity": "HIGH",
                "observation": f"Session ended automatically due to enforcement status: {session.status.value}.",
                "score_deduction": round(deduction, 2),
            })

        # 9. Phone detected
        phone_count = event_counts.get("phone_detected", 0)
        if phone_count > 0:
            cfg = DEDUCTIONS_CONFIG["PHONE_DETECTED"]
            deduction = min(phone_count * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "PHONE_DETECTED",
                "title": cfg["title"],
                "count": phone_count,
                "severity": "HIGH",
                "observation": f"Potential mobile phone presence observed in camera frame ({phone_count} event(s)).",
                "score_deduction": round(deduction, 2),
            })

        # 10. Laptop detected
        laptop_count = event_counts.get("laptop_detected", 0)
        if laptop_count > 0:
            cfg = DEDUCTIONS_CONFIG["LAPTOP_DETECTED"]
            deduction = min(laptop_count * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "LAPTOP_DETECTED",
                "title": cfg["title"],
                "count": laptop_count,
                "severity": "MEDIUM",
                "observation": f"Potential additional laptop/display device observed in camera frame ({laptop_count} event(s)).",
                "score_deduction": round(deduction, 2),
            })

        # 11. Book / notes detected
        book_count = event_counts.get("book_detected", 0)
        if book_count > 0:
            cfg = DEDUCTIONS_CONFIG["BOOK_DETECTED"]
            deduction = min(book_count * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "BOOK_DETECTED",
                "title": cfg["title"],
                "count": book_count,
                "severity": "MEDIUM",
                "observation": f"Potential unauthorized study material / book observed in camera frame ({book_count} event(s)).",
                "score_deduction": round(deduction, 2),
            })

        # 12. Additional person detected
        person_count = event_counts.get("additional_person", 0)
        if person_count > 0:
            cfg = DEDUCTIONS_CONFIG["ADDITIONAL_PERSON_DETECTED"]
            deduction = min(person_count * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "ADDITIONAL_PERSON_DETECTED",
                "title": cfg["title"],
                "count": person_count,
                "severity": "HIGH",
                "observation": f"Potential additional person presence detected in room environment ({person_count} event(s)).",
                "score_deduction": round(deduction, 2),
            })

        # 13. Rapid Answer Changes (Stage 9.3)
        total_rapid = max(rapid_change_clusters, rapid_change_events_count)
        if total_rapid > 0:
            cfg = DEDUCTIONS_CONFIG["RAPID_ANSWER_CHANGES"]
            deduction = min(total_rapid * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "RAPID_ANSWER_CHANGES",
                "title": cfg["title"],
                "count": total_rapid,
                "severity": "MEDIUM" if total_rapid >= 3 else "LOW",
                "observation": f"{total_rapid} rapid answer modification cluster(s) occurred within short intervals.",
                "score_deduction": round(deduction, 2),
            })

        # 14. Unusual Answer Timing (Stage 9.3)
        total_timing_instances = max(1 if very_fast_count >= 4 else 0, unusual_timing_events_count)
        if total_timing_instances > 0:
            cfg = DEDUCTIONS_CONFIG["UNUSUAL_TIMING"]
            deduction = min(total_timing_instances * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "UNUSUAL_TIMING",
                "title": cfg["title"],
                "count": very_fast_count if very_fast_count > 0 else total_timing_instances,
                "severity": "MEDIUM" if very_fast_count >= 6 else "LOW",
                "observation": f"{very_fast_count if very_fast_count > 0 else total_timing_instances} questions were answered within less than 3 seconds each.",
                "score_deduction": round(deduction, 2),
            })

        # 15. Navigation Pattern Anomaly (Stage 9.3)
        total_nav_instances = max(1 if backtrack_count >= 4 else 0, nav_anomaly_events_count)
        if total_nav_instances > 0:
            cfg = DEDUCTIONS_CONFIG["NAVIGATION_ANOMALY"]
            deduction = min(total_nav_instances * cfg["per_event"], cfg["max_deduction"])
            score -= deduction
            evidence_items.append({
                "signal_type": "NAVIGATION_ANOMALY",
                "title": cfg["title"],
                "count": backtrack_count if backtrack_count > 0 else total_nav_instances,
                "severity": "MEDIUM" if backtrack_count >= 6 else "LOW",
                "observation": f"Repeated back-and-forth navigation occurred between several questions ({backtrack_count} backtracking instances).",
                "score_deduction": round(deduction, 2),
            })

        # 16. Combined Behavioural Anomaly (Stage 9.3)
        active_indicators = (
            (1 if total_rapid > 0 else 0) +
            (1 if very_fast_count >= 4 else 0) +
            (1 if backtrack_count >= 4 else 0)
        )
        if active_indicators >= 2 or behavioural_anomaly_events_count > 0:
            cfg = DEDUCTIONS_CONFIG["BEHAVIOURAL_ANOMALY"]
            deduction = cfg["per_event"]
            score -= deduction
            evidence_items.append({
                "signal_type": "BEHAVIOURAL_ANOMALY",
                "title": cfg["title"],
                "count": max(active_indicators, behavioural_anomaly_events_count),
                "severity": "HIGH",
                "observation": "Behavioural anomaly based on multiple observed indicators (rapid answer modifications, short response intervals, and repeated backtracking).",
                "score_deduction": round(deduction, 2),
            })

        # 17. Identity Verification Mismatch (Stage 9.4)
        has_identity_mismatch_confirmed = any(
            (hasattr(ev.event_type, "value") and ev.event_type.value == "IDENTITY_MISMATCH_CONFIRMED")
            or str(ev.event_type) == "IDENTITY_MISMATCH_CONFIRMED"
            for ev in proctoring_events
        ) or session.identity_verification_status == "CONFIRMED_IDENTITY_MISMATCH"

        if has_identity_mismatch_confirmed:
            cfg = DEDUCTIONS_CONFIG["IDENTITY_MISMATCH_CONFIRMED"]
            deduction = cfg["per_event"]
            score -= deduction
            evidence_items.append({
                "signal_type": "IDENTITY_MISMATCH_CONFIRMED",
                "title": cfg["title"],
                "count": 1,
                "severity": "HIGH",
                "observation": "Registered student identity could not be confirmed continuously for the required grace period.",
                "score_deduction": round(deduction, 2),
            })

        # If no evidence items exist
        if not evidence_items:
            evidence_items.append({
                "signal_type": "NO_SIGNALS",
                "title": "Standard Behaviour",
                "count": 0,
                "severity": "INFO",
                "observation": "No significant integrity signals observed.",
                "score_deduction": 0.0,
            })

        # Clamp score between 0.0 and 100.0
        final_score = max(0.0, min(100.0, score))
        risk_level = self.determine_risk_level(final_score)
        recommendation = self.determine_recommendation(risk_level)

        # Build Chronological Timeline
        raw_timeline: List[Dict[str, Any]] = []

        if session.started_at:
            raw_timeline.append({
                "timestamp": session.started_at.isoformat(),
                "dt": session.started_at,
                "event_type": "EXAM_STARTED",
                "label": "Exam Session Started",
                "details": "Student initiated the examination environment.",
                "severity": "INFO",
            })

        for ev in proctoring_events:
            ev_type_str = str(ev.event_type.value) if hasattr(ev.event_type, "value") else str(ev.event_type)
            sev_str = str(ev.severity.value) if hasattr(ev.severity, "value") else str(ev.severity)
            ts = ev.occurred_at or session.created_at

            label_map = {
                "TAB_HIDDEN": "Tab Switch / Window Blur",
                "TAB_SWITCH": "Tab Switch Detected",
                "TAB_VISIBLE": "Returned to Exam Tab",
                "FULLSCREEN_ENTERED": "Entered Fullscreen",
                "FULLSCREEN_EXITED": "Exited Fullscreen Mode",
                "FACE_NOT_DETECTED": "Face Absence Detected",
                "FACE_MISSING": "Face Absence Detected",
                "FACE_DETECTED": "Face Detected in Frame",
                "MULTIPLE_FACES_DETECTED": "Multiple Faces Observed",
                "MULTIPLE_FACES": "Multiple Faces Observed",
                "CAMERA_DISCONNECTED": "Camera Disconnected",
                "MICROPHONE_DISCONNECTED": "Microphone Disconnected",
                "TAB_SWITCH_LIMIT_EXCEEDED": "Tab Switch Limit Exceeded",
                "PHONE_DETECTED": "Potential Mobile Phone Detected",
                "LAPTOP_DETECTED": "Potential Additional Device Detected",
                "BOOK_DETECTED": "Potential Unauthorized Material Detected",
                "ADDITIONAL_PERSON_DETECTED": "Potential Additional Person Observed",
                "OBJECT_DETECTION_STARTED": "Object Monitoring Active",
                "OBJECT_DETECTION_UNAVAILABLE": "Object Monitoring Unavailable",
                "PRE_EXAM_CHECK_STARTED": "Pre-Exam Environment Check Started",
                "PRE_EXAM_CHECK_COMPLETED": "Pre-Exam Environment Check Passed",
                "QUESTION_VIEWED": "Viewed Question",
                "ANSWER_CREATED": "Submitted Answer Draft",
                "ANSWER_CHANGED": "Modified Answer Choice",
                "ANSWER_CLEARED": "Cleared Answer Choice",
                "QUESTION_NAVIGATION": "Navigated Between Questions",
                "RAPID_ANSWER_CHANGES": "Rapid Answer Modification Pattern",
                "UNUSUAL_TIMING": "Unusual Response Timing Pattern",
                "NAVIGATION_ANOMALY": "Navigation Backtracking Anomaly",
                "BEHAVIOURAL_ANOMALY": "Combined Behavioural Anomaly",
                "IDENTITY_VERIFIED": "Identity Verified",
                "IDENTITY_VERIFICATION_FAILED": "Identity Verification Failed",
                "IDENTITY_MISMATCH_STARTED": "Identity Mismatch Started",
                "IDENTITY_VERIFICATION_RESTORED": "Identity Verification Restored",
                "IDENTITY_MISMATCH_CONFIRMED": "Identity Mismatch Confirmed",
            }

            raw_timeline.append({
                "timestamp": ts.isoformat() if ts else None,
                "dt": ts,
                "event_type": ev_type_str,
                "label": label_map.get(ev_type_str, ev_type_str.replace("_", " ").title()),
                "details": f"Recorded proctoring alert (Severity: {sev_str}).",
                "severity": sev_str,
            })

        if session.submitted_at:
            raw_timeline.append({
                "timestamp": session.submitted_at.isoformat(),
                "dt": session.submitted_at,
                "event_type": "EXAM_SUBMITTED",
                "label": f"Exam Session Concluded ({session.status.value})",
                "details": f"Final session submission recorded with status {session.status.value}.",
                "severity": "INFO",
            })

        # Sort timeline chronologically
        raw_timeline.sort(key=lambda x: x["dt"] if x["dt"] else datetime.min)

        # Format timeline for output (drop datetime object)
        formatted_timeline = [
            {
                "timestamp": item["timestamp"],
                "event_type": item["event_type"],
                "label": item["label"],
                "details": item["details"],
                "severity": item["severity"],
            }
            for item in raw_timeline
        ]

        signals_summary = {
            "tab_switches": event_counts["tab_switches"],
            "face_alerts": event_counts["face_not_detected"] + event_counts["multiple_faces"],
            "fullscreen_events": event_counts["fullscreen_exits"],
            "hardware_alerts": event_counts["camera_issues"] + event_counts["microphone_issues"],
            "total_signals": len(proctoring_events),
        }

        return final_score, risk_level, recommendation, evidence_items, formatted_timeline, signals_summary, behavioural_summary

    def analyze_or_update_session_integrity(
        self, db: Session, session: ExamSession
    ) -> IntegrityAnalysis:
        """
        Calculates session integrity analysis and persists/updates the IntegrityAnalysis DB record.
        Idempotent and deterministic.
        """
        proctoring_events = session.proctoring_events or []

        score, risk_level, recommendation, evidence, timeline, signals_summary, behavioural_summary = (
            self.calculate_session_integrity(session, proctoring_events)
        )

        contributing_signals = {
            "risk_level": risk_level,
            "recommendation": recommendation,
            "evidence": evidence,
            "timeline": timeline,
            "signals_summary": signals_summary,
            "behavioural_summary": behavioural_summary,
        }

        summary_text = (
            f"Integrity Score: {score:.1f}/100 ({risk_level} Risk). "
            f"Observed {signals_summary['tab_switches']} tab switch(es), "
            f"{signals_summary['face_alerts']} face alert(s)."
        )

        # Check existing record
        analysis = (
            db.query(IntegrityAnalysis)
            .filter(IntegrityAnalysis.session_id == session.id)
            .first()
        )

        if analysis:
            analysis.integrity_score = score
            analysis.summary = summary_text
            analysis.contributing_signals = contributing_signals
            analysis.analysis_status = AnalysisStatus.COMPLETED
            analysis.updated_at = datetime.utcnow()
        else:
            analysis = IntegrityAnalysis(
                session_id=session.id,
                integrity_score=score,
                analysis_status=AnalysisStatus.COMPLETED,
                summary=summary_text,
                contributing_signals=contributing_signals,
            )
            db.add(analysis)

        db.commit()
        db.refresh(analysis)
        return analysis

    def get_exam_integrity_summary(
        self,
        db: Session,
        exam_id: uuid.UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        risk_level_filter: Optional[str] = None,
    ) -> PaginatedExamIntegrityResponse:
        """
        Returns aggregated exam integrity summary and paginated student session analyses.
        Enforces Examiner ownership security & Admin permission.
        """
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        # RBAC Check
        if current_user.role == UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not authorized to view integrity analysis."
            )
        if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not own this exam."
            )

        # Fetch all completed/submitted/in-progress sessions for this exam
        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.exam_id == exam_id)
            .all()
        )

        items: List[ExamIntegritySummaryItem] = []
        scores: List[float] = []
        high_risk = 0
        mod_risk = 0
        low_risk = 0

        for sess in sessions:
            analysis = self.analyze_or_update_session_integrity(db, sess)
            scores.append(analysis.integrity_score)

            sig = analysis.contributing_signals or {}
            risk = sig.get("risk_level", self.determine_risk_level(analysis.integrity_score))
            signals_sum = sig.get("signals_summary", {})

            if risk == "HIGH":
                high_risk += 1
            elif risk == "MODERATE":
                mod_risk += 1
            else:
                low_risk += 1

            # Search & Risk level filtering
            student_name = f"{sess.student.first_name} {sess.student.last_name}" if sess.student else "Unknown Student"
            student_email = sess.student.email if sess.student else ""

            if search:
                s_lower = search.lower()
                if s_lower not in student_name.lower() and s_lower not in student_email.lower():
                    continue

            if risk_level_filter and risk_level_filter.upper() != risk:
                continue

            items.append(
                ExamIntegritySummaryItem(
                    session_id=sess.id,
                    student_id=sess.student_id,
                    student_name=student_name,
                    student_email=student_email,
                    session_status=sess.status.value,
                    integrity_score=float(analysis.integrity_score),
                    risk_level=risk,
                    analysis_status=analysis.analysis_status,
                    total_signals=signals_sum.get("total_signals", len(sess.proctoring_events or [])),
                    tab_switches=signals_sum.get("tab_switches", 0),
                    face_alerts=signals_sum.get("face_alerts", 0),
                    is_flagged=sess.is_flagged,
                    submitted_at=sess.submitted_at,
                )
            )

        total_sessions = len(sessions)
        avg_score = round(sum(scores) / len(scores), 2) if scores else 100.0

        # Pagination
        total_items = len(items)
        pages = max(1, math.ceil(total_items / page_size))
        start_idx = (page - 1) * page_size
        paginated_items = items[start_idx : start_idx + page_size]

        return PaginatedExamIntegrityResponse(
            exam_id=exam.id,
            exam_title=exam.title,
            exam_subject=exam.subject,
            total_sessions=total_sessions,
            average_integrity_score=avg_score,
            high_risk_count=high_risk,
            moderate_risk_count=mod_risk,
            low_risk_count=low_risk,
            items=paginated_items,
            total=total_items,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def get_session_integrity_detail(
        self, db: Session, exam_id: uuid.UUID, session_id: uuid.UUID, current_user: User
    ) -> SessionIntegrityDetailResponse:
        """
        Returns detailed integrity analysis for a single exam session.
        Enforces Examiner ownership and session-exam association.
        """
        session = (
            db.query(ExamSession)
            .filter(ExamSession.id == session_id, ExamSession.exam_id == exam_id)
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found for this exam."
            )

        exam = session.exam
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated exam not found.")

        # RBAC Check
        if current_user.role == UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not authorized to view session integrity details."
            )
        if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not own this exam."
            )

        analysis = self.analyze_or_update_session_integrity(db, session)
        sig = analysis.contributing_signals or {}

        student_name = (
            f"{session.student.first_name} {session.student.last_name}"
            if session.student
            else "Unknown Student"
        )
        student_email = session.student.email if session.student else ""

        risk = sig.get("risk_level", self.determine_risk_level(analysis.integrity_score))
        rec = sig.get("recommendation", self.determine_recommendation(risk))
        ev_items = sig.get("evidence", [])
        timeline_items = sig.get("timeline", [])
        signals_sum = sig.get("signals_summary", {})
        beh_sum = sig.get("behavioural_summary", None)

        proctoring_events = session.proctoring_events or []
        mismatch_episodes = sum(1 for e in proctoring_events if str(getattr(e.event_type, "value", e.event_type)) == "IDENTITY_MISMATCH_STARTED")
        confirmed_mismatches = sum(1 for e in proctoring_events if str(getattr(e.event_type, "value", e.event_type)) == "IDENTITY_MISMATCH_CONFIRMED")
        has_verified_event = any(str(getattr(e.event_type, "value", e.event_type)) == "IDENTITY_VERIFIED" for e in proctoring_events)

        identity_summary = {
            "initial_status": "VERIFIED" if (session.identity_verified_at or has_verified_event) else "UNVERIFIED",
            "mismatch_episodes": mismatch_episodes,
            "confirmed_mismatches": confirmed_mismatches,
            "last_status": session.identity_verification_status or "UNVERIFIED",
            "verified_at": session.identity_verified_at.isoformat() if session.identity_verified_at else None,
        }

        return SessionIntegrityDetailResponse(
            id=analysis.id,
            session_id=session.id,
            exam_id=exam.id,
            student_id=session.student_id,
            student_name=student_name,
            student_email=student_email,
            session_status=session.status.value,
            integrity_score=float(analysis.integrity_score),
            risk_level=risk,
            analysis_status=analysis.analysis_status,
            summary=analysis.summary or "",
            recommendation=rec,
            evidence=ev_items,
            timeline=timeline_items,
            signals_summary=signals_sum,
            behavioural_summary=beh_sum,
            identity_summary=identity_summary,
            generated_at=analysis.generated_at or analysis.created_at,
            reviewed_at=analysis.reviewed_at,
        )

    def get_student_integrity_overview(
        self, db: Session, current_user: User
    ) -> StudentIntegrityOverviewResponse:
        """
        Returns student-safe aggregated integrity summary and exam-wise integrity history.
        Only accesses sessions owned by the authenticated student.
        """
        if current_user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role.value}' is not authorized."
            )

        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.student_id == current_user.id)
            .order_by(ExamSession.created_at.desc())
            .all()
        )

        exam_items: List[StudentExamIntegrityItem] = []
        scores: List[float] = []
        high_risk_count = 0
        moderate_risk_count = 0
        low_risk_count = 0
        completed_count = 0

        for session in sessions:
            analysis = self.analyze_or_update_session_integrity(db, session)
            score = float(analysis.integrity_score)
            risk = self.determine_risk_level(score)
            scores.append(score)

            if risk == "HIGH":
                high_risk_count += 1
            elif risk == "MODERATE":
                moderate_risk_count += 1
            else:
                low_risk_count += 1

            if session.status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]:
                completed_count += 1

            exam_title = session.exam.title if session.exam else "Examination"
            event_count = len(session.proctoring_events or [])

            exam_items.append(
                StudentExamIntegrityItem(
                    exam_id=session.exam_id,
                    exam_title=exam_title,
                    session_id=session.id,
                    started_at=session.started_at or session.created_at,
                    submitted_at=session.submitted_at,
                    integrity_score=score,
                    risk_level=risk,
                    event_count=event_count,
                    status=session.status.value,
                )
            )

        avg_score = round(sum(scores) / len(scores), 1) if scores else 100.0

        summary = StudentIntegritySummary(
            exams_monitored=len(sessions),
            exams_completed=completed_count,
            average_integrity_score=avg_score,
            high_risk_count=high_risk_count,
            moderate_risk_count=moderate_risk_count,
            low_risk_count=low_risk_count,
        )

        return StudentIntegrityOverviewResponse(
            summary=summary,
            exams=exam_items,
        )

    def get_student_session_integrity_detail(
        self, db: Session, session_id: uuid.UUID, current_user: User
    ) -> StudentSessionIntegrityDetailResponse:
        """
        Returns student-safe detailed integrity evaluation for a specific examination session.
        Enforces strict student session ownership.
        """
        if current_user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role.value}' is not authorized."
            )

        session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found."
            )

        # Strict IDOR prevention
        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session."
            )

        exam = session.exam
        exam_title = exam.title if exam else "Examination"
        exam_subject = exam.subject if exam else None

        analysis = self.analyze_or_update_session_integrity(db, session)
        score = float(analysis.integrity_score)
        risk = self.determine_risk_level(score)

        if risk == "LOW":
            status_explanation = "Integrity monitoring detected normal examination activity consistent with expected standards."
        elif risk == "MODERATE":
            status_explanation = "Integrity monitoring recorded minor session events or window transitions during this examination."
        else:
            status_explanation = "Integrity monitoring recorded multiple notable session events or environment anomalies during this examination."

        proctoring_events = session.proctoring_events or []

        # Count events by category
        tab_count = 0
        fullscreen_count = 0
        face_not_detected_count = 0
        multiple_faces_count = 0
        hardware_count = 0
        phone_count = 0
        laptop_count = 0
        book_count = 0
        person_count = 0

        for ev in proctoring_events:
            etype = str(ev.event_type.value) if hasattr(ev.event_type, "value") else str(ev.event_type)
            if etype in ["TAB_HIDDEN", "TAB_SWITCH", "TAB_SWITCH_LIMIT_EXCEEDED"]:
                tab_count += 1
            elif etype in ["FULLSCREEN_EXITED"]:
                fullscreen_count += 1
            elif etype in ["FACE_NOT_DETECTED", "FACE_MISSING"]:
                face_not_detected_count += 1
            elif etype in ["MULTIPLE_FACES_DETECTED", "MULTIPLE_FACES"]:
                multiple_faces_count += 1
            elif etype in ["CAMERA_DISCONNECTED", "MICROPHONE_DISCONNECTED", "CAMERA_PERMISSION_DENIED", "MICROPHONE_PERMISSION_DENIED"]:
                hardware_count += 1
            elif etype == "PHONE_DETECTED":
                phone_count += 1
            elif etype == "LAPTOP_DETECTED":
                laptop_count += 1
            elif etype == "BOOK_DETECTED":
                book_count += 1
            elif etype == "ADDITIONAL_PERSON_DETECTED":
                person_count += 1

        event_summary = {
            "tab_switches": tab_count,
            "fullscreen_exits": fullscreen_count,
            "face_absence": face_not_detected_count,
            "multiple_faces": multiple_faces_count,
            "hardware_issues": hardware_count,
            "phone_detected": phone_count,
            "laptop_detected": laptop_count,
            "book_detected": book_count,
            "additional_person": person_count,
            "total_events": len(proctoring_events),
        }

        # Build chronological timeline
        label_map = {
            "TAB_HIDDEN": "Tab Switch / Window Blur",
            "TAB_SWITCH": "Tab Switch Detected",
            "TAB_VISIBLE": "Returned to Exam Tab",
            "FULLSCREEN_ENTERED": "Entered Fullscreen",
            "FULLSCREEN_EXITED": "Exited Fullscreen Mode",
            "FACE_NOT_DETECTED": "Face Absence Detected",
            "FACE_MISSING": "Face Absence Detected",
            "FACE_DETECTED": "Face Detected in Frame",
            "MULTIPLE_FACES_DETECTED": "Multiple Faces Observed",
            "MULTIPLE_FACES": "Multiple Faces Observed",
            "CAMERA_DISCONNECTED": "Camera Disconnected",
            "MICROPHONE_DISCONNECTED": "Microphone Disconnected",
            "TAB_SWITCH_LIMIT_EXCEEDED": "Tab Switch Limit Exceeded",
            "PHONE_DETECTED": "Potential Mobile Phone Detected",
            "LAPTOP_DETECTED": "Potential Additional Display Detected",
            "BOOK_DETECTED": "Potential Unauthorized Study Material Detected",
            "ADDITIONAL_PERSON_DETECTED": "Potential Additional Person Observed",
            "OBJECT_DETECTION_STARTED": "Object Monitoring Active",
            "OBJECT_DETECTION_UNAVAILABLE": "Object Monitoring Unavailable",
            "PRE_EXAM_CHECK_STARTED": "Pre-Exam Environment Check Started",
            "PRE_EXAM_CHECK_COMPLETED": "Pre-Exam Environment Check Passed",
            "QUESTION_VIEWED": "Viewed Question",
            "ANSWER_CREATED": "Answer Choice Submitted",
            "ANSWER_CHANGED": "Answer Choice Modified",
            "ANSWER_CLEARED": "Answer Choice Cleared",
            "QUESTION_NAVIGATION": "Navigated Between Questions",
            "RAPID_ANSWER_CHANGES": "Rapid Answer Modifications",
            "UNUSUAL_TIMING": "Short Response Timing",
            "NAVIGATION_ANOMALY": "Repeated Navigation Backtracking",
            "BEHAVIOURAL_ANOMALY": "Combined Behavioural Indicator",
            "IDENTITY_VERIFIED": "Identity Verified",
            "IDENTITY_VERIFICATION_FAILED": "Identity Verification Failed",
            "IDENTITY_MISMATCH_STARTED": "Identity Mismatch Started",
            "IDENTITY_VERIFICATION_RESTORED": "Identity Verification Restored",
            "IDENTITY_MISMATCH_CONFIRMED": "Identity Mismatch Confirmed",
        }

        description_map = {
            "TAB_HIDDEN": "Application focus was lost or the browser tab was switched.",
            "TAB_SWITCH": "A tab switch occurred away from the examination window.",
            "TAB_VISIBLE": "Returned focus to the examination tab.",
            "FULLSCREEN_ENTERED": "Full-screen examination mode was activated.",
            "FULLSCREEN_EXITED": "Full-screen examination mode was exited.",
            "FACE_NOT_DETECTED": "No face was detected within the camera frame.",
            "FACE_MISSING": "No face was detected within the camera frame.",
            "FACE_DETECTED": "Face recognized and aligned within the camera frame.",
            "MULTIPLE_FACES_DETECTED": "More than one face was visible within the camera frame.",
            "MULTIPLE_FACES": "More than one face was visible within the camera frame.",
            "CAMERA_DISCONNECTED": "Camera stream was disconnected or interrupted.",
            "MICROPHONE_DISCONNECTED": "Microphone audio feed was disconnected or interrupted.",
            "TAB_SWITCH_LIMIT_EXCEEDED": "The permitted tab switch threshold was exceeded.",
            "PHONE_DETECTED": "A mobile device was observed in the camera frame.",
            "LAPTOP_DETECTED": "An additional computer screen or laptop was observed.",
            "BOOK_DETECTED": "Books or printed study materials were detected in view.",
            "ADDITIONAL_PERSON_DETECTED": "An additional person was observed in the test area.",
            "RAPID_ANSWER_CHANGES": "Rapid answer modifications observed in a short time frame.",
            "UNUSUAL_TIMING": "Questions answered in less than standard reading duration.",
            "NAVIGATION_ANOMALY": "Multiple back-and-forth navigation passes across questions.",
            "BEHAVIOURAL_ANOMALY": "Multiple automated behavioural signals noted.",
        }

        events_list: List[StudentProctoringEventItem] = []
        for ev in sorted(proctoring_events, key=lambda x: x.occurred_at or datetime.min):
            etype = str(ev.event_type.value) if hasattr(ev.event_type, "value") else str(ev.event_type)
            sev = str(ev.severity.value) if hasattr(ev.severity, "value") else str(ev.severity)
            title = label_map.get(etype, etype.replace("_", " ").title())
            desc = description_map.get(etype, f"Recorded proctoring alert (Severity: {sev}).")
            events_list.append(
                StudentProctoringEventItem(
                    event_type=etype,
                    title=title,
                    occurred_at=ev.occurred_at,
                    description=desc,
                    severity=sev,
                )
            )

        # Behavioural metrics
        beh_dict = (analysis.contributing_signals or {}).get("behavioural_summary")
        if beh_dict and isinstance(beh_dict, dict) and beh_dict.get("questions_visited") is not None:
            beh_metrics = StudentBehaviouralMetrics(
                metrics_available=True,
                questions_visited=beh_dict.get("questions_visited"),
                questions_answered=beh_dict.get("questions_answered"),
                answer_changes=beh_dict.get("answer_change_count"),
                answers_cleared=beh_dict.get("clear_count"),
                navigation_count=beh_dict.get("navigation_count"),
                backtracking_count=beh_dict.get("backtrack_count"),
                avg_question_time=beh_dict.get("average_question_time"),
                median_question_time=beh_dict.get("median_question_time"),
                rapid_change_clusters=beh_dict.get("rapid_change_count"),
            )
        else:
            beh_metrics = StudentBehaviouralMetrics(metrics_available=False)

        # Environment monitoring
        env_alerts_total = phone_count + laptop_count + book_count + person_count
        if env_alerts_total == 0:
            env_status = "NORMAL"
            env_explanation = "No external objects or unauthorized devices were flagged in the examination environment."
        else:
            env_status = "ALERTS_RECORDED"
            env_explanation = f"Environment monitoring observed {env_alerts_total} potential object or presence alert(s) during this examination session."

        env_monitoring = StudentEnvironmentMonitoring(
            phone_detected_count=phone_count,
            laptop_detected_count=laptop_count,
            book_detected_count=book_count,
            additional_person_count=person_count,
            status=env_status,
            explanation=env_explanation,
        )

        return StudentSessionIntegrityDetailResponse(
            exam_id=session.exam_id,
            exam_title=exam_title,
            exam_subject=exam_subject,
            session_id=session.id,
            session_status=session.status.value,
            started_at=session.started_at or session.created_at,
            submitted_at=session.submitted_at,
            integrity_score=score,
            risk_level=risk,
            status_explanation=status_explanation,
            event_count=len(proctoring_events),
            event_summary=event_summary,
            events=events_list,
            behavioural_metrics=beh_metrics,
            environment_monitoring=env_monitoring,
        )


integrity_service = IntegrityService()

