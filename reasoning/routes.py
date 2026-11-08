"""Flask presentation endpoints for a single signed-in user's eligibility."""
from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import select
from models import db, Candidate, Job
from requirements_models import JobRequirement
from .adapter import assess
from .live_knowledge import build_live_knowledge


def register_reasoning_routes(app):
    @app.route('/jobs/<int:job_id>/eligibility')
    @login_required
    def check_eligibility(job_id):
        job = db.get_or_404(Job, job_id)
        if not job.is_active and job.posted_by != current_user.id:
            abort(404)
        candidate = db.session.scalar(select(Candidate).where(
            Candidate.user_id == current_user.id))
        if candidate is None:
            flash('Create your candidate profile before checking eligibility.', 'warning')
            return redirect(url_for('profile'))
        requirements = db.session.scalars(select(JobRequirement).where(
            JobRequirement.job_id == job.id).order_by(JobRequirement.id)).all()
        analysis = assess(candidate, job, requirements)
        return render_template('eligibility_result.html', job=job,
                               candidate=candidate, analysis=analysis)

    @app.route('/knowledge-explorer')
    @login_required
    def knowledge_explorer():
        from flask import request
        candidate = db.session.scalar(select(Candidate).where(
            Candidate.user_id == current_user.id))
        jobs = db.session.scalars(select(Job).where(
            (Job.is_active.is_(True)) | (Job.posted_by == current_user.id)
        ).order_by(Job.created_at.desc(), Job.id.desc())).all()
        selected_id = request.args.get('job_id', type=int)
        if selected_id is None and jobs:
            selected_id = jobs[0].id
        job = next((j for j in jobs if j.id == selected_id), None)
        if selected_id is not None and job is None:
            abort(404)
        requirements = (db.session.scalars(select(JobRequirement).where(
            JobRequirement.job_id == job.id).order_by(JobRequirement.id)).all()
            if job else [])
        live = build_live_knowledge(candidate, job, requirements)
        return render_template('knowledge_explorer.html',
                               candidate=candidate, job=job, jobs=jobs, live=live)

    @app.route('/knowledge-explorer/graph.dot')
    @login_required
    def knowledge_graph_dot():
        from flask import request, Response
        import json
        candidate = db.session.scalar(select(Candidate).where(
            Candidate.user_id == current_user.id))
        jobs = db.session.scalars(select(Job).where(
            (Job.is_active.is_(True)) | (Job.posted_by == current_user.id)
        ).order_by(Job.created_at.desc(), Job.id.desc())).all()
        selected_id = request.args.get('job_id', type=int)
        job = next((j for j in jobs if j.id == selected_id), None) if selected_id else (jobs[0] if jobs else None)
        if selected_id and job is None:
            abort(404)
        requirements = (db.session.scalars(select(JobRequirement).where(
            JobRequirement.job_id == job.id)).all() if job else [])
        live = build_live_knowledge(candidate, job, requirements)
        lines = ['digraph TalentIQ {', '  rankdir=LR;', '  node [shape=ellipse];']
        if candidate:
            lines.append('  candidate [label=' + json.dumps('Candidate #' + str(candidate.id)) + '];')
        if job:
            lines.append('  job [label=' + json.dumps(job.title) + '];')
        for n in live['graph']:
            key = 'record_' + str(n['id'])
            lines.append('  ' + key + ' [label=' + json.dumps(n['category'] + ': ' + n['name']) + '];')
            if n['has']:
                lines.append('  candidate -> ' + key + ' [label=' + json.dumps('has-' + n['category'].lower()) + '];')
            if n['required']:
                lines.append('  job -> ' + key + ' [label=' + json.dumps('requires-' + n['category'].lower()) + '];')
        lines.append('}')
        return Response('\n'.join(lines), mimetype='text/vnd.graphviz')
