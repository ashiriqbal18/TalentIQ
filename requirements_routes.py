from domain_config import REQUIREMENT_CATEGORIES, REQUIREMENT_IMPORTANCE, PROFICIENCY_LEVELS, MAX_JOB_REQUIREMENTS

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app
)

from flask_login import login_required, current_user
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from models import db, Job
from requirements_models import JobRequirement


CATEGORIES = set(REQUIREMENT_CATEGORIES)
IMPORTANCE = set(REQUIREMENT_IMPORTANCE)
LEVELS = set(PROFICIENCY_LEVELS) | {""}
MAX_ROWS = MAX_JOB_REQUIREMENTS


# ==========================================================
# HELPERS
# ==========================================================

def get_owned_job(job_id):
    job = db.get_or_404(Job, job_id)

    if job.posted_by != current_user.id:
        abort(403)

    return job


def get_owned_requirement(job_id, requirement_id):
    requirement = db.session.scalar(
        select(JobRequirement).where(
            JobRequirement.id == requirement_id,
            JobRequirement.job_id == job_id
        )
    )

    if requirement is None:
        abort(404)

    return requirement


def validate_requirement():
    category = request.form.get(
        "category", ""
    ).strip().lower()

    name = " ".join(
        request.form.get("name", "").split()
    )

    level = request.form.get(
        "level", ""
    ).strip()

    importance = request.form.get(
        "importance", ""
    ).strip().lower()

    if category not in CATEGORIES:
        return None, "Invalid requirement category."

    if not name or len(name) > 150:
        return None, "Enter a valid requirement name."

    if importance not in IMPORTANCE:
        return None, "Select a valid importance."

    if level not in LEVELS:
        return None, "Invalid skill level."

    if category != "skill":
        level = None
    else:
        level = level or None

    return {
        "category": category,
        "name": name,
        "level": level,
        "importance": importance
    }, None


def requirement_exists(job_id, category, name, exclude_id=None):
    query = select(JobRequirement).where(
        JobRequirement.job_id == job_id,
        JobRequirement.category == category,
        func.lower(JobRequirement.name) == name.lower()
    )

    if exclude_id is not None:
        query = query.where(
            JobRequirement.id != exclude_id
        )

    return db.session.scalar(query) is not None


def back_to_requirements(job_id):
    return redirect(
        url_for(
            "manage_job_requirements",
            job_id=job_id
        )
    )


# ==========================================================
# REGISTER REQUIREMENTS ROUTES
# ==========================================================

def register_requirements_routes(app):

    # ------------------------------------------------------
    # 1. DISPLAY SAVED REQUIREMENTS
    # ------------------------------------------------------

    @app.route(
        "/my-jobs/<int:job_id>/requirements",
        methods=["GET"]
    )
    @login_required
    def manage_job_requirements(job_id):

        job = get_owned_job(job_id)

        requirements = db.session.scalars(
            select(JobRequirement)
            .where(
                JobRequirement.job_id == job.id
            )
            .order_by(JobRequirement.id.asc())
        ).all()

        return render_template(
            "job_requirements.html",
            job=job,
            requirements=requirements
        )

    # ------------------------------------------------------
    # 2. ADD NEW REQUIREMENT
    # ------------------------------------------------------

    @app.route(
        "/my-jobs/<int:job_id>/requirements/add",
        methods=["POST"]
    )
    @login_required
    def add_job_requirement(job_id):

        job = get_owned_job(job_id)

        data, error = validate_requirement()

        if error:
            flash(error, "danger")
            return back_to_requirements(job.id)

        count = db.session.scalar(
            select(func.count(JobRequirement.id))
            .where(JobRequirement.job_id == job.id)
        )

        if count >= MAX_ROWS:
            flash(
                f"Maximum {MAX_ROWS} requirements allowed.",
                "danger"
            )
            return back_to_requirements(job.id)

        if requirement_exists(
            job.id,
            data["category"],
            data["name"]
        ):
            flash(
                "This requirement already exists.",
                "warning"
            )
            return back_to_requirements(job.id)

        new_requirement = JobRequirement(
            job_id=job.id,
            category=data["category"],
            name=data["name"],
            level=data["level"],
            importance=data["importance"]
        )

        try:
            db.session.add(new_requirement)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception(
                "Failed to add job requirement"
            )
            flash(
                "Could not add requirement.",
                "danger"
            )
            return back_to_requirements(job.id)

        flash(
            "Requirement added successfully.",
            "success"
        )

        return back_to_requirements(job.id)

    # ------------------------------------------------------
    # 3. EDIT EXISTING REQUIREMENT
    # ------------------------------------------------------

    @app.route(
        "/my-jobs/<int:job_id>/requirements/"
        "<int:requirement_id>/edit",
        methods=["POST"]
    )
    @login_required
    def edit_job_requirement(job_id, requirement_id):

        job = get_owned_job(job_id)

        requirement = get_owned_requirement(
            job.id,
            requirement_id
        )

        data, error = validate_requirement()

        if error:
            flash(error, "danger")
            return back_to_requirements(job.id)

        if requirement_exists(
            job.id,
            data["category"],
            data["name"],
            exclude_id=requirement.id
        ):
            flash(
                "Another requirement with this name "
                "and category already exists.",
                "warning"
            )
            return back_to_requirements(job.id)

        requirement.category = data["category"]
        requirement.name = data["name"]
        requirement.level = data["level"]
        requirement.importance = data["importance"]

        try:
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception(
                "Failed to update job requirement"
            )
            flash(
                "Could not update requirement.",
                "danger"
            )
            return back_to_requirements(job.id)

        flash(
            "Requirement updated successfully.",
            "success"
        )

        return back_to_requirements(job.id)

    # ------------------------------------------------------
    # 4. DELETE EXISTING REQUIREMENT
    # ------------------------------------------------------

    @app.route(
        "/my-jobs/<int:job_id>/requirements/"
        "<int:requirement_id>/delete",
        methods=["POST"]
    )
    @login_required
    def delete_job_requirement(job_id, requirement_id):

        job = get_owned_job(job_id)

        requirement = get_owned_requirement(
            job.id,
            requirement_id
        )

        try:
            db.session.delete(requirement)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception(
                "Failed to delete job requirement"
            )
            flash(
                "Could not delete requirement.",
                "danger"
            )
            return back_to_requirements(job.id)

        flash(
            "Requirement deleted successfully.",
            "success"
        )

        return back_to_requirements(job.id)
