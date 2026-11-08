from domain_config import (
    WORK_TYPES, PROFICIENCY_LEVELS, EDUCATION_LEVELS,
    REQUIREMENT_CATEGORIES, REQUIREMENT_IMPORTANCE, MAX_JOB_REQUIREMENTS
)

import math
import os
from datetime import date
from urllib.parse import urlsplit

from requirements_models import JobRequirement
from requirements_routes import register_requirements_routes

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)

from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from flask_wtf.csrf import CSRFProtect
from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError

from config import Config

from models import (
    db,
    User,
    Candidate,
    Job,
    Evaluation,
    Skill,
    CandidateSkill,
    JobSkill,
    Qualification,
    CandidateQualification,
    Certification,
    CandidateCertification,
    Experience,
    JobPreference
)

# Advanced Job Requirements Builder
from requirements_models import JobRequirement
from requirements_routes import register_requirements_routes
from editing_routes import edit_bp


# ==========================================================
# 1. FLASK APPLICATION CONFIGURATION
# ==========================================================

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.context_processor
def domain_options():
    return dict(work_types=WORK_TYPES,
                proficiency_levels=PROFICIENCY_LEVELS,
                education_levels=EDUCATION_LEVELS,
                requirement_categories=REQUIREMENT_CATEGORIES,
                requirement_importance=REQUIREMENT_IMPORTANCE,
                max_job_requirements=MAX_JOB_REQUIREMENTS)


csrf = CSRFProtect(app)


# ==========================================================
# 2. LOGIN MANAGER
# ==========================================================

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message = (
    "Please sign in to access your TalentIQ workspace."
)
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# ==========================================================
# 3. LANDING PAGE
# ==========================================================

@app.route("/")
def index():
    return render_template("index.html")


# ==========================================================
# 4. USER REGISTRATION
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not full_name or not email or not password:
            flash(
                "All required fields must be filled.",
                "danger"
            )
            return render_template("register.html")

        if len(full_name) > 150 or len(email) > 150:
            flash("Name or email is too long.", "danger")
            return render_template("register.html")

        if (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
            or any(char.isspace() for char in email)
        ):
            flash(
                "Please enter a valid email address.",
                "danger"
            )
            return render_template("register.html")

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        existing_user = db.session.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            flash(
                "An account with this email already exists.",
                "danger"
            )
            return render_template("register.html")

        new_user = User(
            full_name=full_name,
            email=email
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "Unable to register this email.",
                "danger"
            )
            return render_template("register.html")

        flash(
            "Account created successfully. Please sign in.",
            "success"
        )
        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================================================
# 5. USER LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")

        user = db.session.scalar(
            select(User).where(User.email == email)
        )

        if user and user.check_password(password):

            login_user(user)

            flash(
                f"Welcome back, {user.full_name}!",
                "success"
            )

            next_page = request.args.get("next", "")
            parsed = urlsplit(next_page)

            if (
                next_page.startswith("/")
                and not next_page.startswith("//")
                and not next_page.startswith("/\\")
                and not parsed.netloc
                and not parsed.scheme
            ):
                return redirect(next_page)

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ==========================================================
# 6. JOB SEARCH DASHBOARD
# ==========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    keyword = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    work_type = request.args.get("work_type", "").strip()
    experience = request.args.get("experience", "").strip()

    query = Job.query.filter_by(is_active=True)

    if keyword:

        search_pattern = f"%{keyword}%"

        matching_skill_jobs = (
            db.session.query(JobSkill.job_id)
            .join(
                Skill,
                JobSkill.skill_id == Skill.id
            )
            .filter(
                Skill.name.ilike(search_pattern)
            )
        )

        query = query.filter(
            or_(
                Job.title.ilike(search_pattern),
                Job.company.ilike(search_pattern),
                Job.department.ilike(search_pattern),
                Job.description.ilike(search_pattern),
                Job.id.in_(matching_skill_jobs)
            )
        )

    if location:
        query = query.filter(
            Job.location.ilike(f"%{location}%")
        )

    allowed_types = set(WORK_TYPES)

    if work_type in allowed_types:
        query = query.filter_by(work_type=work_type)

    if experience:
        try:
            years = float(experience)

            if math.isfinite(years) and 0 <= years <= 60:
                query = query.filter(
                    Job.min_experience <= years
                )
        except ValueError:
            pass

    page = request.args.get("page", 1, type=int)
    page = max(page, 1)

    pagination = query.order_by(
        Job.created_at.desc(),
        Job.id.desc()
    ).paginate(
        page=page,
        per_page=9,
        error_out=False
    )

    return render_template(
        "dashboard.html",
        jobs=pagination.items,
        pagination=pagination,
        keyword=keyword,
        location=location,
        work_type=work_type,
        experience=experience
    )


# ==========================================================
# 7. POST A NEW JOB
# ==========================================================

@app.route("/post-job", methods=["GET", "POST"])
@login_required
def post_job():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        description = request.form.get(
            "description", ""
        ).strip()

        department = request.form.get(
            "department", ""
        ).strip()

        location = request.form.get(
            "location", ""
        ).strip()

        work_type = request.form.get(
            "work_type", ""
        ).strip()

        if not title or not company or not description:
            flash(
                "Job title, company and description are required.",
                "danger"
            )
            return render_template("post_job.html")

        if (
            len(title) > 150
            or len(company) > 150
            or len(department) > 100
            or len(location) > 150
            or len(description) > 10000
        ):
            flash(
                "One or more fields are too long.",
                "danger"
            )
            return render_template("post_job.html")

        valid_work_types = set(WORK_TYPES)

        if work_type not in valid_work_types:
            flash(
                "Please select a valid employment type.",
                "danger"
            )
            return render_template("post_job.html")

        try:
            min_experience = float(
                request.form.get("min_experience", "0")
            )

            salary_min_text = request.form.get(
                "salary_min", ""
            ).strip()

            salary_max_text = request.form.get(
                "salary_max", ""
            ).strip()

            salary_min = (
                int(salary_min_text)
                if salary_min_text else None
            )

            salary_max = (
                int(salary_max_text)
                if salary_max_text else None
            )

        except ValueError:
            flash(
                "Please enter valid numeric values.",
                "danger"
            )
            return render_template("post_job.html")

        if (
            not math.isfinite(min_experience)
            or min_experience < 0
            or min_experience > 60
        ):
            flash(
                "Experience must be between 0 and 60 years.",
                "danger"
            )
            return render_template("post_job.html")

        if (
            (salary_min is not None and salary_min < 0)
            or (salary_max is not None and salary_max < 0)
        ):
            flash("Salary cannot be negative.", "danger")
            return render_template("post_job.html")

        if (
            salary_min is not None
            and salary_max is not None
            and salary_max < salary_min
        ):
            flash(
                "Maximum salary cannot be less than minimum salary.",
                "danger"
            )
            return render_template("post_job.html")

        new_job = Job(
            title=title,
            company=company,
            description=description,
            department=department or None,
            location=location or None,
            work_type=work_type,
            min_experience=min_experience,
            salary_min=salary_min,
            salary_max=salary_max,
            posted_by=current_user.id,
            is_active=True
        )

        db.session.add(new_job)
        db.session.commit()

        flash(
            "Your job has been published successfully!",
            "success"
        )

        return redirect(
            url_for(
                "job_detail",
                job_id=new_job.id
            )
        )

    return render_template("post_job.html")


# ==========================================================
# 8. VIEW JOB DETAILS
# ==========================================================


# ==========================================================
# 8. VIEW JOB DETAILS WITH REQUIREMENTS
# ==========================================================


@app.route("/jobs/<int:job_id>")
@login_required
def job_detail(job_id):

    job = db.get_or_404(Job, job_id)

    if (
        not job.is_active
        and job.posted_by != current_user.id
    ):
        abort(404)

    requirements = (
        JobRequirement.query
        .filter_by(job_id=job.id)
        .order_by(JobRequirement.id.asc())
        .all()
    )

    skill_requirements = [
        item for item in requirements
        if item.category.lower() == "skill"
    ]

    education_requirements = [
        item for item in requirements
        if item.category.lower() == "education"
    ]

    certification_requirements = [
        item for item in requirements
        if item.category.lower() == "certification"
    ]

    return render_template(
        "job_detail.html",
        job=job,
        requirements=requirements,
        skill_requirements=skill_requirements,
        education_requirements=education_requirements,
        certification_requirements=certification_requirements
    )




# ==========================================================
# 9. MY JOB POSTS
# ==========================================================

@app.route("/my-jobs")
@login_required
def my_jobs():

    jobs = Job.query.filter_by(
        posted_by=current_user.id
    ).order_by(
        Job.created_at.desc(),
        Job.id.desc()
    ).all()

    return render_template(
        "my_jobs.html",
        jobs=jobs
    )


# ==========================================================
# 10. ACTIVATE / DEACTIVATE JOB
# ==========================================================

@app.route(
    "/my-jobs/<int:job_id>/toggle",
    methods=["POST"]
)
@login_required
def toggle_job(job_id):

    job = db.get_or_404(Job, job_id)

    if job.posted_by != current_user.id:
        abort(403)

    job.is_active = not job.is_active
    db.session.commit()

    flash(
        "Job status updated successfully.",
        "success"
    )

    return redirect(url_for("my_jobs"))


# ==========================================================
# 11. USER LOGOUT
# ==========================================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash(
        "You have been signed out successfully.",
        "success"
    )

    return redirect(url_for("login"))


# ==========================================================
# 12. PROFILE HELPERS
# ==========================================================

def my_candidate():

    candidate = db.session.scalar(
        select(Candidate).where(
            Candidate.user_id == current_user.id
        )
    )

    if candidate is None:
        abort(404)

    return candidate


def read_optional_date(field):

    value = request.form.get(field, "").strip()

    if not value:
        return None

    return date.fromisoformat(value)


# ==========================================================
# 13. MY PROFILE
# ==========================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    candidate = db.session.scalar(
        select(Candidate).where(
            Candidate.user_id == current_user.id
        )
    )

    if candidate is None:

        existing_email = db.session.scalar(
            select(Candidate).where(
                func.lower(Candidate.email)
                == current_user.email.lower()
            )
        )

        if existing_email:
            flash(
                "A candidate record already uses your email. "
                "Please contact the administrator to link it safely.",
                "warning"
            )
            return redirect(url_for("dashboard"))

        candidate = Candidate(
            user_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email
        )

        try:
            db.session.add(candidate)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "Unable to create your profile.",
                "danger"
            )
            return redirect(url_for("dashboard"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        phone = request.form.get(
            "phone", ""
        ).strip()

        if not full_name or len(full_name) > 150:
            flash(
                "Please enter a valid full name.",
                "danger"
            )
            return redirect(url_for("profile"))

        if len(phone) > 30:
            flash("Phone number is too long.", "danger")
            return redirect(url_for("profile"))

        candidate.full_name = full_name
        candidate.phone = phone or None
        current_user.full_name = full_name

        db.session.commit()

        flash(
            "Profile updated successfully!",
            "success"
        )
        return redirect(url_for("profile"))

    candidate_skills = db.session.scalars(
        select(CandidateSkill)
        .where(
            CandidateSkill.candidate_id == candidate.id
        )
        .order_by(CandidateSkill.id.desc())
    ).all()

    candidate_qualifications = (
        CandidateQualification.query
        .filter_by(candidate_id=candidate.id)
        .order_by(CandidateQualification.id.desc())
        .all()
    )

    candidate_experiences = (
        Experience.query
        .filter_by(candidate_id=candidate.id)
        .order_by(Experience.start_date.desc())
        .all()
    )

    candidate_certifications = (
        CandidateCertification.query
        .filter_by(candidate_id=candidate.id)
        .order_by(CandidateCertification.id.desc())
        .all()
    )

    preferences = JobPreference.query.filter_by(
        user_id=current_user.id
    ).first()

    return render_template(
        "profile.html",
        candidate=candidate,
        candidate_skills=candidate_skills,
        candidate_qualifications=candidate_qualifications,
        candidate_experiences=candidate_experiences,
        candidate_certifications=candidate_certifications,
        preferences=preferences
    )


# ==========================================================
# 14. ADD PROFILE SKILL
# ==========================================================

@app.route("/profile/skills/add", methods=["POST"])
@login_required
def add_profile_skill():

    candidate = my_candidate()

    skill_name = request.form.get(
        "skill_name", ""
    ).strip()

    proficiency = request.form.get(
        "proficiency", ""
    ).strip()

    allowed_levels = set(PROFICIENCY_LEVELS)

    if not skill_name or len(skill_name) > 100:
        flash("Enter a valid skill name.", "danger")
        return redirect(url_for("profile") + "#skills")

    if proficiency not in allowed_levels:
        flash(
            "Select a valid proficiency level.",
            "danger"
        )
        return redirect(url_for("profile") + "#skills")

    skill = db.session.scalar(
        select(Skill).where(
            func.lower(Skill.name) == skill_name.lower()
        )
    )

    if skill is None:
        skill = Skill(name=skill_name)
        db.session.add(skill)

    try:
        db.session.flush()

        existing = CandidateSkill.query.filter_by(
            candidate_id=candidate.id,
            skill_id=skill.id
        ).first()

        if existing:
            db.session.rollback()
            flash(
                "You have already added this skill.",
                "warning"
            )
            return redirect(url_for("profile") + "#skills")

        candidate_skill = CandidateSkill(
            candidate_id=candidate.id,
            skill_id=skill.id,
            proficiency_level=proficiency
        )

        db.session.add(candidate_skill)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash(
            "Could not save this skill.",
            "danger"
        )
        return redirect(url_for("profile") + "#skills")

    flash("Skill added successfully!", "success")
    return redirect(url_for("profile") + "#skills")


# ==========================================================
# 15. DELETE PROFILE SKILL
# ==========================================================

@app.route(
    "/profile/skills/<int:skill_id>/delete",
    methods=["POST"]
)
@login_required
def delete_profile_skill(skill_id):

    candidate = my_candidate()

    candidate_skill = CandidateSkill.query.filter_by(
        id=skill_id,
        candidate_id=candidate.id
    ).first_or_404()

    db.session.delete(candidate_skill)
    db.session.commit()

    flash(
        "Skill removed successfully.",
        "success"
    )

    return redirect(url_for("profile") + "#skills")


# ==========================================================
# 16. ADD EDUCATION
# ==========================================================

@app.route("/profile/education/add", methods=["POST"])
@login_required
def add_education():

    candidate = my_candidate()

    degree = request.form.get("degree", "").strip()
    level = request.form.get("level", "").strip()
    field = request.form.get("field", "").strip()
    institution = request.form.get(
        "institution", ""
    ).strip()
    year_text = request.form.get(
        "completion_year", ""
    ).strip()

    allowed_levels = set(EDUCATION_LEVELS)

    if (
        not degree
        or len(degree) > 150
        or level not in allowed_levels
        or len(field) > 100
        or not institution
        or len(institution) > 150
    ):
        flash(
            "Enter valid education information.",
            "danger"
        )
        return redirect(url_for("profile") + "#education")

    try:
        year = int(year_text) if year_text else None
    except ValueError:
        flash(
            "Invalid completion year.",
            "danger"
        )
        return redirect(url_for("profile") + "#education")

    if year is not None and not (1950 <= year <= 2100):
        flash(
            "Completion year is invalid.",
            "danger"
        )
        return redirect(url_for("profile") + "#education")

    qualification = db.session.scalar(
        select(Qualification).where(
            func.lower(Qualification.name) == degree.lower()
        )
    )

    if qualification is not None:

        if (
            qualification.level != level
            or (qualification.field or "").lower()
            != field.lower()
        ):
            flash(
                "This qualification name already exists "
                "with a different level or field. "
                "Please use a more specific qualification name.",
                "danger"
            )
            return redirect(url_for("profile") + "#education")

    else:
        qualification = Qualification(
            name=degree,
            level=level,
            field=field or None
        )
        db.session.add(qualification)

    try:
        db.session.flush()

        existing = CandidateQualification.query.filter_by(
            candidate_id=candidate.id,
            qualification_id=qualification.id,
            institution=institution,
            completion_year=year
        ).first()

        if existing:
            db.session.rollback()
            flash("Education already added.", "warning")
            return redirect(url_for("profile") + "#education")

        record = CandidateQualification(
            candidate_id=candidate.id,
            qualification_id=qualification.id,
            institution=institution,
            completion_year=year
        )

        db.session.add(record)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash(
            "Unable to save education.",
            "danger"
        )
        return redirect(url_for("profile") + "#education")

    flash(
        "Education added successfully.",
        "success"
    )
    return redirect(url_for("profile") + "#education")


# ==========================================================
# 17. DELETE EDUCATION
# ==========================================================

@app.route(
    "/profile/education/<int:record_id>/delete",
    methods=["POST"]
)
@login_required
def delete_education(record_id):

    candidate = my_candidate()

    record = CandidateQualification.query.filter_by(
        id=record_id,
        candidate_id=candidate.id
    ).first_or_404()

    db.session.delete(record)
    db.session.commit()

    flash(
        "Education removed successfully.",
        "success"
    )

    return redirect(url_for("profile") + "#education")


# ==========================================================
# 18. ADD WORK EXPERIENCE
# ==========================================================

@app.route("/profile/experience/add", methods=["POST"])
@login_required
def add_experience():

    candidate = my_candidate()

    job_title = request.form.get(
        "job_title", ""
    ).strip()

    company = request.form.get(
        "company", ""
    ).strip()

    is_current = (
        request.form.get("is_current") == "on"
    )

    if (
        not job_title
        or len(job_title) > 150
        or not company
        or len(company) > 150
    ):
        flash(
            "Enter valid experience details.",
            "danger"
        )
        return redirect(url_for("profile") + "#experience")

    try:
        start = date.fromisoformat(
            request.form.get("start_date", "")
        )

        end = (
            None
            if is_current
            else read_optional_date("end_date")
        )
    except (ValueError, TypeError):
        flash("Enter valid dates.", "danger")
        return redirect(url_for("profile") + "#experience")

    if start > date.today():
        flash(
            "Start date cannot be in the future.",
            "danger"
        )
        return redirect(url_for("profile") + "#experience")

    if not is_current and end is None:
        flash(
            "End date is required for a past job.",
            "danger"
        )
        return redirect(url_for("profile") + "#experience")

    if end is not None and (
        end < start or end > date.today()
    ):
        flash(
            "End date is invalid.",
            "danger"
        )
        return redirect(url_for("profile") + "#experience")

    record = Experience(
        candidate_id=candidate.id,
        job_title=job_title,
        company=company,
        start_date=start,
        end_date=end,
        is_current=is_current
    )

    db.session.add(record)
    db.session.commit()

    flash(
        "Work experience added successfully.",
        "success"
    )

    return redirect(url_for("profile") + "#experience")


# ==========================================================
# 19. DELETE WORK EXPERIENCE
# ==========================================================

@app.route(
    "/profile/experience/<int:record_id>/delete",
    methods=["POST"]
)
@login_required
def delete_experience(record_id):

    candidate = my_candidate()

    record = Experience.query.filter_by(
        id=record_id,
        candidate_id=candidate.id
    ).first_or_404()

    db.session.delete(record)
    db.session.commit()

    flash(
        "Work experience removed.",
        "success"
    )

    return redirect(url_for("profile") + "#experience")


# ==========================================================
# 20. ADD CERTIFICATION
# ==========================================================

@app.route("/profile/certification/add", methods=["POST"])
@login_required
def add_certification():

    candidate = my_candidate()

    name = request.form.get("name", "").strip()
    issuer = request.form.get("issuer", "").strip()

    if (
        not name
        or len(name) > 150
        or not issuer
        or len(issuer) > 150
    ):
        flash(
            "Enter valid certification details.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#certifications"
        )

    try:
        issue_date = read_optional_date("issue_date")
        expiry_date = read_optional_date("expiry_date")
    except ValueError:
        flash(
            "Enter valid certificate dates.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#certifications"
        )

    if issue_date and issue_date > date.today():
        flash(
            "Issue date cannot be in the future.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#certifications"
        )

    if expiry_date and issue_date and expiry_date < issue_date:
        flash(
            "Expiry date cannot precede issue date.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#certifications"
        )

    certification = db.session.scalar(
        select(Certification).where(
            func.lower(Certification.name) == name.lower()
        )
    )

    if certification is not None:

        existing_issuer = (
            certification.issuing_organization or ""
        ).lower()

        if existing_issuer != issuer.lower():
            flash(
                "This certification name already exists "
                "with a different issuing organization. "
                "Please use a more specific certificate name.",
                "danger"
            )
            return redirect(
                url_for("profile") + "#certifications"
            )

    else:
        certification = Certification(
            name=name,
            issuing_organization=issuer
        )
        db.session.add(certification)

    try:
        db.session.flush()

        existing = CandidateCertification.query.filter_by(
            candidate_id=candidate.id,
            certification_id=certification.id,
            issue_date=issue_date
        ).first()

        if existing:
            db.session.rollback()
            flash(
                "Certification already added.",
                "warning"
            )
            return redirect(
                url_for("profile") + "#certifications"
            )

        record = CandidateCertification(
            candidate_id=candidate.id,
            certification_id=certification.id,
            issue_date=issue_date,
            expiry_date=expiry_date
        )

        db.session.add(record)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash(
            "Unable to save certification.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#certifications"
        )

    flash(
        "Certification added successfully.",
        "success"
    )

    return redirect(
        url_for("profile") + "#certifications"
    )


# ==========================================================
# 21. DELETE CERTIFICATION
# ==========================================================

@app.route(
    "/profile/certification/<int:record_id>/delete",
    methods=["POST"]
)
@login_required
def delete_certification(record_id):

    candidate = my_candidate()

    record = CandidateCertification.query.filter_by(
        id=record_id,
        candidate_id=candidate.id
    ).first_or_404()

    db.session.delete(record)
    db.session.commit()

    flash(
        "Certification removed successfully.",
        "success"
    )

    return redirect(
        url_for("profile") + "#certifications"
    )


# ==========================================================
# 22. SAVE JOB PREFERENCES
# ==========================================================

@app.route("/profile/preferences", methods=["POST"])
@login_required
def save_preferences():

    my_candidate()

    title = request.form.get(
        "preferred_title", ""
    ).strip()

    location = request.form.get(
        "preferred_location", ""
    ).strip()

    work_type = request.form.get(
        "preferred_work_type", ""
    ).strip()

    allowed_types = set(WORK_TYPES) | {""}

    if (
        len(title) > 150
        or len(location) > 150
        or work_type not in allowed_types
    ):
        flash(
            "Invalid job preferences.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#preferences"
        )

    try:
        min_text = request.form.get(
            "salary_min", ""
        ).strip()

        max_text = request.form.get(
            "salary_max", ""
        ).strip()

        salary_min = (
            int(min_text) if min_text else None
        )
        salary_max = (
            int(max_text) if max_text else None
        )

    except ValueError:
        flash(
            "Enter valid salary values.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#preferences"
        )

    if (
        (salary_min is not None and salary_min < 0)
        or (salary_max is not None and salary_max < 0)
        or (
            salary_min is not None
            and salary_max is not None
            and salary_max < salary_min
        )
    ):
        flash(
            "Invalid salary range.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#preferences"
        )

    preferences = JobPreference.query.filter_by(
        user_id=current_user.id
    ).first()

    if preferences is None:
        preferences = JobPreference(
            user_id=current_user.id
        )
        db.session.add(preferences)

    preferences.preferred_title = title or None
    preferences.preferred_location = location or None
    preferences.preferred_work_type = work_type or None
    preferences.expected_salary_min = salary_min
    preferences.expected_salary_max = salary_max

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "Unable to save preferences.",
            "danger"
        )
        return redirect(
            url_for("profile") + "#preferences"
        )

    flash(
        "Job preferences saved successfully.",
        "success"
    )

    return redirect(
        url_for("profile") + "#preferences"
    )


# ==========================================================
# 23. ADVANCED JOB REQUIREMENTS BUILDER
# ==========================================================

# Registers:
#
# GET  /my-jobs/<job_id>/requirements
# POST /my-jobs/<job_id>/requirements
#
# Includes:
# - Skills
# - Education requirements
# - Certification requirements
# - Mandatory / Preferred selection
# - Skill proficiency levels
# - Job ownership validation
#
# IMPORTANT:
# Register routes BEFORE db.create_all()
# and BEFORE app.run().

register_requirements_routes(app)
app.register_blueprint(edit_bp)

# Connect the dynamic CT-351 Horn inference/report routes.
from reasoning.routes import register_reasoning_routes
register_reasoning_routes(app)


# ==========================================================
# 24. DATABASE INITIALIZATION
# ==========================================================

with app.app_context():

    db.create_all()

    print("Database initialized successfully!")


# ==========================================================
# 25. RUN FLASK APPLICATION
# ==========================================================

if __name__ == "__main__":

    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
