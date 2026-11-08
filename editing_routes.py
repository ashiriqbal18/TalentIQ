from domain_config import WORK_TYPES, PROFICIENCY_LEVELS, EDUCATION_LEVELS
"""Authenticated, owner-checked edit screens for jobs and candidate profile records.

All modifications retain row IDs. Shared Skill/Qualification/Certification catalog rows
are never edited globally; candidate associations are repointed when needed.
"""
from datetime import date
import math
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from models import (
    db, Job, Candidate, CandidateSkill, Skill,
    CandidateQualification, Qualification,
    Experience, CandidateCertification, Certification,
)

edit_bp = Blueprint('editing', __name__)


def _candidate():
    candidate = db.session.scalar(select(Candidate).where(Candidate.user_id == current_user.id))
    if candidate is None:
        abort(404)
    return candidate


def _text(field, maximum, mandatory=False):
    value = request.form.get(field, '').strip()
    if len(value) > maximum or (mandatory and not value):
        raise ValueError(f'Invalid {field.replace("_", " ")}.')
    return value


def _date(field):
    raw = request.form.get(field, '').strip()
    return date.fromisoformat(raw) if raw else None


def _safe_commit(destination):
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('This change conflicts with another saved record.', 'danger')
        return redirect(destination)
    flash('Changes saved successfully.', 'success')
    return redirect(destination)


@edit_bp.route('/my-jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = db.get_or_404(Job, job_id)
    if job.posted_by != current_user.id:
        abort(403)

    if request.method == 'POST':
        try:
            title = _text('title', 150, True)
            company = _text('company', 150, True)
            description = _text('description', 10000, True)
            department = _text('department', 100)
            location = _text('location', 150)
            work_type = _text('work_type', 30, True)
            if work_type not in WORK_TYPES:
                raise ValueError('Choose a valid employment type.')
            years = float(request.form.get('min_experience', '0'))
            if not math.isfinite(years) or not 0 <= years <= 60:
                raise ValueError('Experience must be between 0 and 60 years.')
            salary_min_text = request.form.get('salary_min', '').strip()
            salary_max_text = request.form.get('salary_max', '').strip()
            salary_min = int(salary_min_text) if salary_min_text else None
            salary_max = int(salary_max_text) if salary_max_text else None
            if any(n is not None and n < 0 for n in (salary_min, salary_max)):
                raise ValueError('Salaries cannot be negative.')
            if salary_min is not None and salary_max is not None and salary_max < salary_min:
                raise ValueError('Maximum salary must be at least minimum salary.')
        except (ValueError, TypeError) as exc:
            flash(str(exc) or 'Please enter valid values.', 'danger')
            return render_template('post_job.html', job=job, editing=True)

        job.title = title
        job.company = company
        job.description = description
        job.department = department or None
        job.location = location or None
        job.work_type = work_type
        job.min_experience = years
        job.salary_min = salary_min
        job.salary_max = salary_max
        # Existing status, ownership, ID and requirements are preserved.
        return _safe_commit(url_for('my_jobs'))

    return render_template('post_job.html', job=job, editing=True)


KINDS = {
    'skill': CandidateSkill,
    'education': CandidateQualification,
    'experience': Experience,
    'certification': CandidateCertification,
}


@edit_bp.route('/profile/<kind>/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile_record(kind, record_id):
    if kind not in KINDS:
        abort(404)
    candidate = _candidate()
    record = db.session.scalar(
        select(KINDS[kind]).where(
            KINDS[kind].id == record_id,
            KINDS[kind].candidate_id == candidate.id
        )
    )
    if record is None:
        abort(404)

    destination = url_for('profile') + '#' + {
        'skill': 'skills', 'education': 'education',
        'experience': 'experience', 'certification': 'certifications'
    }[kind]

    if request.method == 'POST':
        try:
            if kind == 'skill':
                name = _text('skill_name', 100, True)
                proficiency = _text('proficiency', 30, True)
                if proficiency not in PROFICIENCY_LEVELS:
                    raise ValueError('Select a valid proficiency level.')
                catalog = db.session.scalar(
                    select(Skill).where(func.lower(Skill.name) == name.lower())
                )
                if catalog is None:
                    catalog = Skill(name=name)
                    db.session.add(catalog)
                    db.session.flush()
                record.skill_id = catalog.id
                record.proficiency_level = proficiency

            elif kind == 'education':
                name = _text('degree', 150, True)
                level = _text('level', 50, True)
                field = _text('field', 100)
                institution = _text('institution', 150, True)
                if level not in EDUCATION_LEVELS:
                    raise ValueError('Select a valid education level.')
                year_raw = request.form.get('completion_year', '').strip()
                year = int(year_raw) if year_raw else None
                if year is not None and not 1950 <= year <= 2100:
                    raise ValueError('Completion year is outside the accepted range.')
                catalog = db.session.scalar(
                    select(Qualification).where(func.lower(Qualification.name) == name.lower())
                )
                if catalog is None:
                    catalog = Qualification(name=name, level=level, field=field or None)
                    db.session.add(catalog)
                    db.session.flush()
                elif catalog.level != level or (catalog.field or '').casefold() != field.casefold():
                    raise ValueError('Qualification name already belongs to a different level/field; use a more specific name.')
                record.qualification_id = catalog.id
                record.institution = institution
                record.completion_year = year

            elif kind == 'experience':
                title = _text('job_title', 150, True)
                company = _text('company', 150, True)
                start = _date('start_date')
                current = request.form.get('is_current') == 'on'
                end = None if current else _date('end_date')
                if start is None or start > date.today():
                    raise ValueError('Enter a valid start date that is not in the future.')
                if not current and end is None:
                    raise ValueError('End date is required for a past position.')
                if end is not None and (end < start or end > date.today()):
                    raise ValueError('End date must fall between start date and today.')
                record.job_title = title
                record.company = company
                record.start_date = start
                record.end_date = end
                record.is_current = current

            elif kind == 'certification':
                name = _text('name', 150, True)
                issuer = _text('issuer', 150, True)
                issued = _date('issue_date')
                expiry = _date('expiry_date')
                if issued is not None and issued > date.today():
                    raise ValueError('Issue date cannot be in the future.')
                if expiry is not None and issued is not None and expiry < issued:
                    raise ValueError('Expiry date cannot be before issue date.')
                catalog = db.session.scalar(
                    select(Certification).where(func.lower(Certification.name) == name.lower())
                )
                if catalog is None:
                    catalog = Certification(name=name, issuing_organization=issuer)
                    db.session.add(catalog)
                    db.session.flush()
                elif (catalog.issuing_organization or '').casefold() != issuer.casefold():
                    raise ValueError('This certification name belongs to another issuer; use a more specific name.')
                record.certification_id = catalog.id
                record.issue_date = issued
                record.expiry_date = expiry

        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc) or 'Invalid values.', 'danger')
            return render_template('edit_profile_record.html', kind=kind, record=record)
        except IntegrityError:
            db.session.rollback()
            flash('Unable to save. Another record already uses this item.', 'danger')
            return redirect(destination)

        return _safe_commit(destination)

    return render_template('edit_profile_record.html', kind=kind, record=record)
