
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ==========================================================
# DATABASE INITIALIZATION
# ==========================================================

db = SQLAlchemy()


# ==========================================================
# 1. USER MODEL
# ==========================================================

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False
    )

    # One user can post multiple jobs
    posted_jobs = db.relationship(
        "Job",
        back_populates="owner",
        foreign_keys="Job.posted_by"
    )

    # One user can have one candidate profile
    candidate_profile = db.relationship(
        "Candidate",
        back_populates="user",
        uselist=False
    )

    def set_password(self, password):

        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.email}>"


# ==========================================================
# 2. CANDIDATE MODEL
# ==========================================================

class Candidate(db.Model):

    __tablename__ = "candidates"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Link candidate profile with registered user
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(30),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    user = db.relationship(
        "User",
        back_populates="candidate_profile"
    )

    skills = db.relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    qualifications = db.relationship(
        "CandidateQualification",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    certifications = db.relationship(
        "CandidateCertification",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    experiences = db.relationship(
        "Experience",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    evaluations = db.relationship(
        "Evaluation",
        back_populates="candidate"
    )

    def __repr__(self):
        return f"<Candidate {self.full_name}>"


# ==========================================================
# 3. JOB MODEL
# ==========================================================

class Job(db.Model):

    __tablename__ = "jobs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    company = db.Column(
        db.String(150),
        nullable=True
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    department = db.Column(
        db.String(100),
        nullable=True
    )

    location = db.Column(
        db.String(150),
        nullable=True
    )

    work_type = db.Column(
        db.String(30),
        nullable=True
    )

    min_experience = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    salary_min = db.Column(
        db.Integer,
        nullable=True
    )

    salary_max = db.Column(
        db.Integer,
        nullable=True
    )

    posted_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    owner = db.relationship(
        "User",
        back_populates="posted_jobs",
        foreign_keys=[posted_by]
    )

    skills = db.relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    qualifications = db.relationship(
        "JobQualification",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    certifications = db.relationship(
        "JobCertification",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    evaluations = db.relationship(
        "Evaluation",
        back_populates="job"
    )

    def __repr__(self):
        return f"<Job {self.title}>"


# ==========================================================
# 4. SKILL MODEL
# ==========================================================

class Skill(db.Model):

    __tablename__ = "skills"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=True
    )

    candidate_skills = db.relationship(
        "CandidateSkill",
        back_populates="skill"
    )

    job_skills = db.relationship(
        "JobSkill",
        back_populates="skill"
    )

    def __repr__(self):
        return f"<Skill {self.name}>"


# ==========================================================
# 5. CANDIDATE SKILLS
# ==========================================================

class CandidateSkill(db.Model):

    __tablename__ = "candidate_skills"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id"),
        nullable=False
    )

    skill_id = db.Column(
        db.Integer,
        db.ForeignKey("skills.id"),
        nullable=False
    )

    proficiency_level = db.Column(
        db.String(30),
        nullable=True
    )

    candidate = db.relationship(
        "Candidate",
        back_populates="skills"
    )

    skill = db.relationship(
        "Skill",
        back_populates="candidate_skills"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "candidate_id",
            "skill_id",
            name="uq_candidate_skill"
        ),
    )


# ==========================================================
# 6. JOB SKILLS
# ==========================================================

class JobSkill(db.Model):

    __tablename__ = "job_skills"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    skill_id = db.Column(
        db.Integer,
        db.ForeignKey("skills.id"),
        nullable=False
    )

    is_mandatory = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    min_proficiency = db.Column(
        db.String(30),
        nullable=True
    )

    job = db.relationship(
        "Job",
        back_populates="skills"
    )

    skill = db.relationship(
        "Skill",
        back_populates="job_skills"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "job_id",
            "skill_id",
            name="uq_job_skill"
        ),
    )


# ==========================================================
# 7. QUALIFICATION MODEL
# ==========================================================

class Qualification(db.Model):

    __tablename__ = "qualifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    level = db.Column(
        db.String(50),
        nullable=False
    )

    field = db.Column(
        db.String(100),
        nullable=True
    )

    candidate_qualifications = db.relationship(
        "CandidateQualification",
        back_populates="qualification"
    )

    job_qualifications = db.relationship(
        "JobQualification",
        back_populates="qualification"
    )


# ==========================================================
# 8. CANDIDATE QUALIFICATIONS
# ==========================================================

class CandidateQualification(db.Model):

    __tablename__ = "candidate_qualifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id"),
        nullable=False
    )

    qualification_id = db.Column(
        db.Integer,
        db.ForeignKey("qualifications.id"),
        nullable=False
    )

    institution = db.Column(
        db.String(150),
        nullable=True
    )

    completion_year = db.Column(
        db.Integer,
        nullable=True
    )

    candidate = db.relationship(
        "Candidate",
        back_populates="qualifications"
    )

    qualification = db.relationship(
        "Qualification",
        back_populates="candidate_qualifications"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "candidate_id",
            "qualification_id",
            "institution",
            "completion_year",
            name="uq_candidate_qualification"
        ),
    )


# ==========================================================
# 9. JOB QUALIFICATIONS
# ==========================================================

class JobQualification(db.Model):

    __tablename__ = "job_qualifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    qualification_id = db.Column(
        db.Integer,
        db.ForeignKey("qualifications.id"),
        nullable=False
    )

    is_mandatory = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    job = db.relationship(
        "Job",
        back_populates="qualifications"
    )

    qualification = db.relationship(
        "Qualification",
        back_populates="job_qualifications"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "job_id",
            "qualification_id",
            name="uq_job_qualification"
        ),
    )


# ==========================================================
# 10. CERTIFICATION MODEL
# ==========================================================

class Certification(db.Model):

    __tablename__ = "certifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    issuing_organization = db.Column(
        db.String(150),
        nullable=True
    )

    candidate_certifications = db.relationship(
        "CandidateCertification",
        back_populates="certification"
    )

    job_certifications = db.relationship(
        "JobCertification",
        back_populates="certification"
    )


# ==========================================================
# 11. CANDIDATE CERTIFICATIONS
# ==========================================================

class CandidateCertification(db.Model):

    __tablename__ = "candidate_certifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id"),
        nullable=False
    )

    certification_id = db.Column(
        db.Integer,
        db.ForeignKey("certifications.id"),
        nullable=False
    )

    issue_date = db.Column(
        db.Date,
        nullable=True
    )

    expiry_date = db.Column(
        db.Date,
        nullable=True
    )

    candidate = db.relationship(
        "Candidate",
        back_populates="certifications"
    )

    certification = db.relationship(
        "Certification",
        back_populates="candidate_certifications"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "candidate_id",
            "certification_id",
            "issue_date",
            name="uq_candidate_certification"
        ),
    )


# ==========================================================
# 12. JOB CERTIFICATIONS
# ==========================================================

class JobCertification(db.Model):

    __tablename__ = "job_certifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    certification_id = db.Column(
        db.Integer,
        db.ForeignKey("certifications.id"),
        nullable=False
    )

    is_mandatory = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    job = db.relationship(
        "Job",
        back_populates="certifications"
    )

    certification = db.relationship(
        "Certification",
        back_populates="job_certifications"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "job_id",
            "certification_id",
            name="uq_job_certification"
        ),
    )


# ==========================================================
# 13. EXPERIENCE MODEL
# ==========================================================

class Experience(db.Model):

    __tablename__ = "experiences"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id"),
        nullable=False
    )

    job_title = db.Column(
        db.String(150),
        nullable=False
    )

    company = db.Column(
        db.String(150),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=True
    )

    is_current = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    candidate = db.relationship(
        "Candidate",
        back_populates="experiences"
    )


# ==========================================================
# 14. EVALUATION MODEL
# ==========================================================

class Evaluation(db.Model):

    __tablename__ = "evaluations"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id"),
        nullable=False
    )

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    result = db.Column(
        db.String(30),
        nullable=False
    )

    explanation = db.Column(
        db.Text,
        nullable=True
    )

    reasoning_method = db.Column(
        db.String(30),
        nullable=False
    )

    evaluated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False
    )

    candidate = db.relationship(
        "Candidate",
        back_populates="evaluations"
    )

    job = db.relationship(
        "Job",
        back_populates="evaluations"
    )

    def __repr__(self):
        return f"<Evaluation {self.id}: {self.result}>"



class JobPreference(db.Model):
    __tablename__ = "job_preferences"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    preferred_title = db.Column(db.String(150))
    preferred_location = db.Column(db.String(150))
    preferred_work_type = db.Column(db.String(30))

    expected_salary_min = db.Column(db.Integer)
    expected_salary_max = db.Column(db.Integer)

    user = db.relationship(
        "User",
        backref=db.backref(
            "job_preference",
            uselist=False
        )
    )
