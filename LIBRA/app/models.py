from datetime import datetime

from . import db


# ============================================================
# ACADEMIC LEVEL
# ============================================================

class AcademicLevel(db.Model):
    __tablename__ = "academic_levels"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    level_code = db.Column(
        db.String(10),
        unique=True,
        nullable=False
    )

    academic_level = db.Column(
        db.String(100),
        nullable=False
    )

    programs = db.relationship(
        "Program",
        back_populates="academic_level",
        lazy=True
    )


# ============================================================
# DEPARTMENT / COLLEGE
# ============================================================

class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    department_code = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    department_college = db.Column(
        db.String(200),
        nullable=False
    )

    programs = db.relationship(
        "Program",
        back_populates="department",
        lazy=True
    )


# ============================================================
# PROGRAM
# ============================================================

class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    academic_level_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_levels.id"),
        nullable=False
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False
    )

    program_name = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    note = db.Column(
        db.String(255),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    academic_level = db.relationship(
        "AcademicLevel",
        back_populates="programs"
    )

    department = db.relationship(
        "Department",
        back_populates="programs"
    )

    theses = db.relationship(
        "Thesis",
        back_populates="program",
        lazy=True
    )


# ============================================================
# THESIS
# ============================================================

class Thesis(db.Model):
    __tablename__ = "theses"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    thesis_code = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    title = db.Column(
        db.String(500),
        nullable=False
    )

    author_researchers = db.Column(
        db.String(500),
        nullable=False
    )

    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id"),
        nullable=False
    )

    year_published = db.Column(
        db.Integer,
        nullable=False
    )

    abstract = db.Column(
        db.Text,
        nullable=False
    )

    keywords = db.Column(
        db.Text,
        nullable=False
    )

    research_field = db.Column(
        db.String(255),
        nullable=False
    )

    research_topic = db.Column(
        db.String(255),
        nullable=False
    )

    research_subtopic = db.Column(
        db.String(255),
        nullable=True
    )

    shelf_location = db.Column(
        db.String(100),
        nullable=False
    )

    availability = db.Column(
        db.Enum(
            "Available",
            "Borrowed"
        ),
        nullable=False,
        default="Available"
    )

    is_archived = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    program = db.relationship(
        "Program",
        back_populates="theses"
    )

    borrowing_requests = db.relationship(
        "BorrowingRequest",
        back_populates="thesis",
        lazy=True
    )


# ============================================================
# ADMIN
# ============================================================

class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    display_name = db.Column(
        db.String(200),
        nullable=False
    )

    role = db.Column(
        db.Enum(
            "Administrator",
            "Librarian"
        ),
        nullable=False,
        default="Librarian"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# ============================================================
# BORROWING REQUEST
# ============================================================

class BorrowingRequest(db.Model):
    __tablename__ = "borrowing_requests"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    request_id = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    thesis_id = db.Column(
        db.Integer,
        db.ForeignKey("theses.id"),
        nullable=False
    )

    full_name = db.Column(
        db.String(200),
        nullable=False
    )

    gender = db.Column(
        db.Enum(
            "Female",
            "Male",
            "Prefer not to say"
        ),
        nullable=False
    )

    age = db.Column(
        db.Integer,
        nullable=False
    )

    user_type = db.Column(
        db.Enum(
            "Student",
            "Faculty"
        ),
        nullable=False
    )

    academic_level_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_levels.id"),
        nullable=True
    )

    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id"),
        nullable=True
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=True
    )

    year_level = db.Column(
        db.String(50),
        nullable=True
    )

    address = db.Column(
        db.String(500),
        nullable=False
    )

    duration_hours = db.Column(
        db.Numeric(5, 2),
        nullable=False
    )

    requested_borrowing_time = db.Column(
        db.DateTime,
        nullable=False
    )

    expected_return_time = db.Column(
        db.DateTime,
        nullable=False
    )

    borrowing_location = db.Column(
        db.Enum(
            "Within Library Only",
            "Outside Library / Campus"
        ),
        nullable=False
    )

    request_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    status = db.Column(
        db.Enum(
            "Requested",
            "Borrowed",
            "Returned"
        ),
        nullable=False,
        default="Requested"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    thesis = db.relationship(
        "Thesis",
        back_populates="borrowing_requests"
    )

    transaction = db.relationship(
        "Transaction",
        back_populates="borrowing_request",
        uselist=False
    )


# ============================================================
# TRANSACTION
# ============================================================

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    transaction_id = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    borrowing_request_id = db.Column(
        db.Integer,
        db.ForeignKey("borrowing_requests.id"),
        unique=True,
        nullable=False
    )

    thesis_id = db.Column(
        db.Integer,
        db.ForeignKey("theses.id"),
        nullable=False
    )

    date_time_borrowed = db.Column(
        db.DateTime,
        nullable=False
    )

    expected_return_time = db.Column(
        db.DateTime,
        nullable=False
    )

    borrowing_location = db.Column(
        db.Enum(
            "Within Library Only",
            "Outside Library / Campus"
        ),
        nullable=False
    )

    actual_return_time = db.Column(
        db.DateTime,
        nullable=True
    )

    status = db.Column(
        db.Enum(
            "Borrowed",
            "Returned"
        ),
        nullable=False,
        default="Borrowed"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    borrowing_request = db.relationship(
        "BorrowingRequest",
        back_populates="transaction"
    )


# ============================================================
# SEARCH LOG
# ============================================================

class SearchLog(db.Model):
    __tablename__ = "search_logs"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    search_id = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    searched_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    search_query = db.Column(
        db.String(500),
        nullable=False
    )

    normalized_query = db.Column(
        db.String(500),
        nullable=False
    )

    topic_bucket = db.Column(
        db.String(255),
        nullable=True
    )

    academic_level_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_levels.id"),
        nullable=True
    )

    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id"),
        nullable=True
    )

    research_field_filter = db.Column(
        db.String(255),
        nullable=True
    )

    result_count = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    clicked_thesis_id = db.Column(
        db.Integer,
        db.ForeignKey("theses.id"),
        nullable=True
    )