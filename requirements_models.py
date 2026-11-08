from models import db, Job


class JobRequirement(db.Model):
    __tablename__ = "job_requirements"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey(f"{Job.__tablename__}.id", ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(db.String(20), nullable=False)  # skill / education / certification
    name = db.Column(db.String(150), nullable=False)
    level = db.Column(db.String(30), nullable=True)  # for skills only
    importance = db.Column(db.String(10), nullable=False, default="mandatory")

    __table_args__ = (
        db.CheckConstraint("category IN ('skill','education','certification')", name="ck_job_requirement_category"),
        db.CheckConstraint("importance IN ('mandatory','preferred')", name="ck_job_requirement_importance"),
    )
