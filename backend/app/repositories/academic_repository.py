import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, func

from app.models.academic import College, Department, Section
from app.models.user import User, UserRole
from app.models.exam import Exam, ExamTargetType, ExamTargetStudent


class AcademicRepository:
    # --- COLLEGE METHODS ---
    @staticmethod
    def get_college_by_id(db: Session, college_id: uuid.UUID) -> Optional[College]:
        return db.scalar(select(College).where(College.id == college_id))

    @staticmethod
    def get_college_by_code(db: Session, code: str) -> Optional[College]:
        return db.scalar(select(College).where(College.code == code.upper().strip()))

    @staticmethod
    def list_colleges(db: Session, is_active: Optional[bool] = None) -> List[College]:
        query = select(College)
        if is_active is not None:
            query = query.where(College.is_active == is_active)
        return list(db.scalars(query.order_by(College.name.asc())).all())

    @staticmethod
    def create_college(db: Session, name: str, code: str) -> College:
        college = College(
            name=name.strip(),
            code=code.upper().strip(),
            is_active=True
        )
        db.add(college)
        db.commit()
        db.refresh(college)
        return college

    @staticmethod
    def update_college(db: Session, college: College, name: Optional[str] = None, code: Optional[str] = None, is_active: Optional[bool] = None) -> College:
        if name is not None:
            college.name = name.strip()
        if code is not None:
            college.code = code.upper().strip()
        if is_active is not None:
            college.is_active = is_active
        db.commit()
        db.refresh(college)
        return college

    # --- DEPARTMENT METHODS ---
    @staticmethod
    def get_department_by_id(db: Session, department_id: uuid.UUID) -> Optional[Department]:
        return db.scalar(select(Department).where(Department.id == department_id))

    @staticmethod
    def get_department_by_code(db: Session, college_id: uuid.UUID, code: str) -> Optional[Department]:
        return db.scalar(
            select(Department).where(
                and_(
                    Department.college_id == college_id,
                    Department.code == code.upper().strip()
                )
            )
        )

    @staticmethod
    def list_departments(db: Session, college_id: Optional[uuid.UUID] = None, is_active: Optional[bool] = None) -> List[Department]:
        query = select(Department)
        if college_id is not None:
            query = query.where(Department.college_id == college_id)
        if is_active is not None:
            query = query.where(Department.is_active == is_active)
        return list(db.scalars(query.order_by(Department.name.asc())).all())

    @staticmethod
    def create_department(db: Session, college_id: uuid.UUID, name: str, code: str) -> Department:
        dept = Department(
            college_id=college_id,
            name=name.strip(),
            code=code.upper().strip(),
            is_active=True
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def update_department(db: Session, dept: Department, name: Optional[str] = None, code: Optional[str] = None, is_active: Optional[bool] = None) -> Department:
        if name is not None:
            dept.name = name.strip()
        if code is not None:
            dept.code = code.upper().strip()
        if is_active is not None:
            dept.is_active = is_active
        db.commit()
        db.refresh(dept)
        return dept

    # --- SECTION METHODS ---
    @staticmethod
    def get_section_by_id(db: Session, section_id: uuid.UUID) -> Optional[Section]:
        return db.scalar(select(Section).where(Section.id == section_id))

    @staticmethod
    def list_sections(db: Session, department_id: Optional[uuid.UUID] = None, year_of_study: Optional[int] = None, is_active: Optional[bool] = None) -> List[Section]:
        query = select(Section)
        if department_id is not None:
            query = query.where(Section.department_id == department_id)
        if year_of_study is not None:
            query = query.where(Section.year_of_study == year_of_study)
        if is_active is not None:
            query = query.where(Section.is_active == is_active)
        return list(db.scalars(query.order_by(Section.year_of_study.asc(), Section.name.asc())).all())

    @staticmethod
    def create_section(db: Session, department_id: uuid.UUID, year_of_study: int, name: str, code: str) -> Section:
        section = Section(
            department_id=department_id,
            year_of_study=year_of_study,
            name=name.strip(),
            code=code.upper().strip(),
            is_active=True
        )
        db.add(section)
        db.commit()
        db.refresh(section)
        return section

    @staticmethod
    def update_section(db: Session, section: Section, name: Optional[str] = None, code: Optional[str] = None, is_active: Optional[bool] = None) -> Section:
        if name is not None:
            section.name = name.strip()
        if code is not None:
            section.code = code.upper().strip()
        if is_active is not None:
            section.is_active = is_active
        db.commit()
        db.refresh(section)
        return section

    # --- ACADEMIC ASSIGNMENTS ---
    @staticmethod
    def update_student_academic_profile(
        db: Session,
        student: User,
        college_id: Optional[uuid.UUID],
        department_id: Optional[uuid.UUID],
        year_of_study: Optional[int],
        section_id: Optional[uuid.UUID]
    ) -> User:
        student.college_id = college_id
        student.department_id = department_id
        student.year_of_study = year_of_study
        student.section_id = section_id
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def update_user_college(db: Session, user: User, college_id: Optional[uuid.UUID]) -> User:
        user.college_id = college_id
        db.commit()
        db.refresh(user)
        return user

    # --- ELIGIBILITY & TARGET COUNTING ---
    @staticmethod
    def count_eligible_students(
        db: Session,
        college_id: Optional[uuid.UUID],
        target_type: Optional[ExamTargetType],
        department_id: Optional[uuid.UUID] = None,
        year_of_study: Optional[int] = None,
        section_id: Optional[uuid.UUID] = None,
        specific_student_ids: Optional[List[uuid.UUID]] = None
    ) -> int:
        """Calculates exact count of students matching target criteria within examiner's college."""
        query = select(func.count(User.id)).where(
            and_(
                User.role == UserRole.STUDENT,
                User.is_active == True
            )
        )
        if college_id is not None:
            query = query.where(User.college_id == college_id)

        if not target_type or target_type == ExamTargetType.COLLEGE:
            pass  # Entire college
        elif target_type == ExamTargetType.DEPARTMENT and department_id:
            query = query.where(User.department_id == department_id)
        elif target_type == ExamTargetType.YEAR:
            if department_id:
                query = query.where(User.department_id == department_id)
            if year_of_study:
                query = query.where(User.year_of_study == year_of_study)
        elif target_type == ExamTargetType.SECTION and section_id:
            query = query.where(User.section_id == section_id)
        elif target_type == ExamTargetType.SPECIFIC_STUDENTS and specific_student_ids:
            query = query.where(User.id.in_(specific_student_ids))

        return db.scalar(query) or 0

    @staticmethod
    def is_student_authorized_for_exam(db: Session, student: User, exam: Exam) -> bool:
        """Determines if a student belongs to the exam's target audience."""
        # 1. Examiner ownership / college scope check
        examiner = db.scalar(select(User).where(User.id == exam.created_by))
        if examiner and examiner.college_id:
            # Student must belong to same college (if student has a college_id)
            if student.college_id and student.college_id != examiner.college_id:
                return False

        # 2. Check targeting parameters
        if not exam.target_type or exam.target_type == ExamTargetType.COLLEGE:
            return True

        if exam.target_type == ExamTargetType.DEPARTMENT:
            return student.department_id == exam.target_department_id

        if exam.target_type == ExamTargetType.YEAR:
            matches_dept = (exam.target_department_id is None) or (student.department_id == exam.target_department_id)
            matches_year = (exam.target_year_of_study is None) or (student.year_of_study == exam.target_year_of_study)
            return matches_dept and matches_year

        if exam.target_type == ExamTargetType.SECTION:
            return student.section_id == exam.target_section_id

        if exam.target_type == ExamTargetType.SPECIFIC_STUDENTS:
            target_entry = db.scalar(
                select(ExamTargetStudent).where(
                    and_(
                        ExamTargetStudent.exam_id == exam.id,
                        ExamTargetStudent.student_id == student.id
                    )
                )
            )
            return target_entry is not None

        return True


academic_repository = AcademicRepository()
