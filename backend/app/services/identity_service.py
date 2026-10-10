import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.exam_session import ExamSession
from app.models.proctoring import ProctoringEvent, ProctoringEventType, EventSeverity

SIMILARITY_THRESHOLD = 0.80  # Cosine similarity threshold for landmark geometry embeddings
GRACE_PERIOD_SECONDS = 180.0  # 3 minutes continuous mismatch grace period
CURRENT_DESCRIPTOR_VERSION = 2  # Current zero-centered landmark descriptor version


class IdentityService:
    @staticmethod
    def calculate_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Calculates Cosine Similarity between two normalized float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)
        return max(-1.0, min(1.0, similarity))

    def get_identity_status(self, current_user: User) -> Dict[str, Any]:
        """Returns identity status including template descriptor version validation."""
        is_registered = bool(current_user.is_face_registered and current_user.face_embedding)
        version = getattr(current_user, "face_descriptor_version", None)
        is_valid_version = is_registered and (version == CURRENT_DESCRIPTOR_VERSION)
        requires_re_enrollment = is_registered and not is_valid_version

        return {
            "is_face_registered": is_valid_version,
            "face_registered_at": current_user.face_registered_at if current_user.face_registered_at else None,
            "descriptor_version": version,
            "requires_re_enrollment": requires_re_enrollment,
            "current_system_version": CURRENT_DESCRIPTOR_VERSION,
        }

    def register_student_face(
        self,
        db: Session,
        student_user: User,
        face_embedding: List[float],
        consent_given: bool,
        descriptor_version: int = CURRENT_DESCRIPTOR_VERSION,
    ) -> Dict[str, Any]:
        """
        Stores student face landmark embedding template securely.
        Enforces explicit student consent and tracks descriptor version.
        """
        if not consent_given:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit consent is required to register your face reference for identity verification."
            )

        if not face_embedding or len(face_embedding) < 16:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid face embedding data. Please ensure your face is clearly visible."
            )

        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in face_embedding):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid face embedding data: non-finite or invalid numerical values."
            )

        if all(x == 0.0 for x in face_embedding):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid face embedding data: all zero values."
            )

        import logging
        import hashlib
        logger = logging.getLogger("app.identity")

        norm = math.sqrt(sum(x * x for x in face_embedding))
        is_all_zeros = all(x == 0.0 for x in face_embedding)
        digest = hashlib.sha256(str(face_embedding[:8]).encode("utf-8")).hexdigest()[:12]
        min_val = min(face_embedding) if face_embedding else 0.0
        max_val = max(face_embedding) if face_embedding else 0.0

        logger.info(
            f"[FACE_REGISTRATION_DIAGNOSTIC] user_id={student_user.id} embedding_exists=True length={len(face_embedding)} "
            f"type={type(face_embedding).__name__} min={min_val:.4f} max={max_val:.4f} "
            f"norm={norm:.4f} is_all_zeros={is_all_zeros} digest={digest} descriptor_version={descriptor_version}"
        )

        now = datetime.now(timezone.utc)
        student_user.face_embedding = face_embedding
        student_user.face_descriptor_version = descriptor_version
        student_user.is_face_registered = True
        student_user.face_registered_at = now

        db.commit()
        db.refresh(student_user)

        return {
            "is_face_registered": True,
            "face_registered_at": now,
            "message": "Face registration completed successfully.",
            "descriptor_version": descriptor_version,
        }

    def clear_student_face(self, db: Session, student_user: User) -> Dict[str, Any]:
        """Clears registered face embedding template for student."""
        student_user.face_embedding = None
        student_user.face_descriptor_version = None
        student_user.is_face_registered = False
        student_user.face_registered_at = None

        db.commit()
        return {"message": "Registered face reference cleared successfully."}

    def verify_session_identity(
        self,
        db: Session,
        session: ExamSession,
        student_user: User,
        live_embedding: List[float],
        descriptor_version: int = CURRENT_DESCRIPTOR_VERSION,
    ) -> Dict[str, Any]:
        """
        Verifies live frame face embedding against student registered face template.
        Enforces descriptor version compatibility and manages state transitions and grace periods.
        """
        if session.student_id != student_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session.",
            )

        if not student_user.is_face_registered or not student_user.face_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student face reference is not registered. Please register your face in Profile settings."
            )

        # Enforce descriptor version compatibility - require safe re-enrollment if template is legacy v1
        stored_version = getattr(student_user, "face_descriptor_version", None) or 1
        if stored_version != CURRENT_DESCRIPTOR_VERSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TEMPLATE_VERSION_MISMATCH: Face template was registered with an earlier descriptor version (v1). Safe re-enrollment is required in Profile."
            )

        if descriptor_version != CURRENT_DESCRIPTOR_VERSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LIVE_DESCRIPTOR_VERSION_MISMATCH: Live frame descriptor version {descriptor_version} is incompatible with required version {CURRENT_DESCRIPTOR_VERSION}."
            )

        if not live_embedding or len(live_embedding) < 16:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid live camera face data."
            )

        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in live_embedding):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid live camera face data: non-finite or invalid numerical values."
            )

        if all(x == 0.0 for x in live_embedding):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid live camera face data: all zero values."
            )

        now = datetime.now(timezone.utc)
        similarity = self.calculate_cosine_similarity(live_embedding, student_user.face_embedding)
        is_match = similarity >= SIMILARITY_THRESHOLD

        import logging
        logger = logging.getLogger("app.identity")

        reg_vec = student_user.face_embedding or []
        norm_reg = math.sqrt(sum(x * x for x in reg_vec))
        norm_live = math.sqrt(sum(x * x for x in live_embedding))

        meta = session.session_metadata or {}
        prev_status = session.identity_verification_status or "UNVERIFIED"
        mismatch_start_str = meta.get("identity_mismatch_started_at")
        target_status = "VERIFIED" if is_match else ("VERIFICATION_FAILED" if prev_status in ["UNVERIFIED", "VERIFICATION_FAILED"] else "TEMPORARILY_UNVERIFIED")

        logger.warning(
            f"[IDENTITY_VERIFICATION_AUDIT] auth_user_id={student_user.id} "
            f"session_id={session.id} session_student_id={session.student_id} "
            f"template_owner_id={student_user.id} "
            f"template_exists={student_user.is_face_registered} "
            f"registered_version={stored_version} live_version={descriptor_version} "
            f"registered_dim={len(reg_vec)} current_dim={len(live_embedding)} "
            f"registered_norm={norm_reg:.4f} current_norm={norm_live:.4f} "
            f"similarity={similarity:.4f} threshold={SIMILARITY_THRESHOLD:.2f} "
            f"match={is_match} transition='{prev_status}'->'{target_status}'"
        )

        if is_match:
            # If identity was previously unverified or mismatching, record restoration event
            if prev_status in ["TEMPORARILY_UNVERIFIED", "IDENTITY_MISMATCH", "CONFIRMED_IDENTITY_MISMATCH"]:
                ev = ProctoringEvent(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    event_type=ProctoringEventType.IDENTITY_VERIFICATION_RESTORED,
                    severity=EventSeverity.INFO,
                    occurred_at=now,
                    event_metadata={"reason": "Live face re-matched registered student template."},
                )
                db.add(ev)
            elif prev_status == "UNVERIFIED":
                ev = ProctoringEvent(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    event_type=ProctoringEventType.IDENTITY_VERIFIED,
                    severity=EventSeverity.INFO,
                    occurred_at=now,
                    event_metadata={"reason": "Pre-exam identity verification succeeded."},
                )
                db.add(ev)

            meta["identity_mismatch_started_at"] = None
            session.session_metadata = meta
            session.identity_verification_status = "VERIFIED"
            session.identity_verified_at = now
            db.commit()

            return {
                "verified": True,
                "status": "VERIFIED",
                "message": "Identity verified successfully.",
                "mismatch_duration_seconds": 0.0,
                "similarity": round(similarity, 4),
                "descriptor_version": CURRENT_DESCRIPTOR_VERSION,
            }

        else:
            # Identity mismatch detected
            if prev_status in ["UNVERIFIED", "VERIFICATION_FAILED"] or not mismatch_start_str:
                meta["identity_mismatch_started_at"] = now.isoformat()
                session.session_metadata = meta
                status_str = "VERIFICATION_FAILED" if prev_status in ["UNVERIFIED", "VERIFICATION_FAILED"] else "TEMPORARILY_UNVERIFIED"
                session.identity_verification_status = status_str

                ev = ProctoringEvent(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    event_type=ProctoringEventType.IDENTITY_MISMATCH_STARTED,
                    severity=EventSeverity.LOW,
                    occurred_at=now,
                    event_metadata={"reason": "Identity verification could not confirm student face match."},
                )
                db.add(ev)
                db.commit()

                msg = (
                    "Identity verification failed. Detected face does not match registered student."
                    if status_str == "VERIFICATION_FAILED"
                    else "Identity could not be confirmed. Please return to the camera position."
                )

                return {
                    "verified": False,
                    "status": status_str,
                    "message": msg,
                    "mismatch_duration_seconds": 0.0,
                    "similarity": round(similarity, 4),
                    "descriptor_version": CURRENT_DESCRIPTOR_VERSION,
                }
            else:
                mismatch_start_dt = datetime.fromisoformat(mismatch_start_str)
                if mismatch_start_dt.tzinfo is None:
                    mismatch_start_dt = mismatch_start_dt.replace(tzinfo=timezone.utc)
                duration_seconds = (now - mismatch_start_dt).total_seconds()

                if duration_seconds >= GRACE_PERIOD_SECONDS:
                    if session.identity_verification_status != "CONFIRMED_IDENTITY_MISMATCH":
                        session.identity_verification_status = "CONFIRMED_IDENTITY_MISMATCH"
                        session.is_flagged = True
                        session.flag_reason = "IDENTITY_MISMATCH_CONFIRMED"

                        ev = ProctoringEvent(
                            id=uuid.uuid4(),
                            session_id=session.id,
                            event_type=ProctoringEventType.IDENTITY_MISMATCH_CONFIRMED,
                            severity=EventSeverity.HIGH,
                            occurred_at=now,
                            event_metadata={
                                "duration_seconds": duration_seconds,
                                "reason": f"Continuous identity mismatch for {int(duration_seconds)}s.",
                            },
                        )
                        db.add(ev)
                        db.commit()

                    return {
                        "verified": False,
                        "status": "CONFIRMED_IDENTITY_MISMATCH",
                        "message": "Identity verification could not be confirmed for the required period. Session flagged for review.",
                        "mismatch_duration_seconds": duration_seconds,
                        "similarity": round(similarity, 4),
                        "descriptor_version": CURRENT_DESCRIPTOR_VERSION,
                    }
                else:
                    return {
                        "verified": False,
                        "status": "TEMPORARILY_UNVERIFIED",
                        "message": "Identity could not be confirmed. Please return to the camera position.",
                        "mismatch_duration_seconds": duration_seconds,
                        "similarity": round(similarity, 4),
                        "descriptor_version": CURRENT_DESCRIPTOR_VERSION,
                    }


identity_service = IdentityService()
