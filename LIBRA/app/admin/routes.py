import uuid
from functools import wraps
from datetime import date, datetime

import os

from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    current_app
)

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as RLImage,
    KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from sqlalchemy import func, or_
from werkzeug.security import check_password_hash

from . import bp

from app import db

from app.models import (
    Admin,
    Thesis,
    BorrowingRequest,
    Transaction,
    SearchLog,
    AcademicLevel,
    Department,
    Program,
)

from io import BytesIO

from flask import send_file

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm

# ============================================================
# ADMIN LOGIN REQUIRED
# ============================================================

def admin_login_required(view_function):

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        if not session.get("admin_id"):

            return redirect(
                url_for("admin.login")
            )

        return view_function(
            *args,
            **kwargs
        )

    return wrapped_view


# ============================================================
# ADMIN LOGIN
# ============================================================

@bp.route("/login", methods=["GET", "POST"])
def login():

    if session.get("admin_id"):

        return redirect(
            url_for("admin.dashboard")
        )

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        admin = (
            Admin.query
            .filter_by(
                username=username
            )
            .first()
        )

        if not admin:

            error = (
                "Invalid username or password."
            )

        elif not admin.is_active:

            error = (
                "This administrator account is inactive."
            )

        elif not check_password_hash(
            admin.password_hash,
            password
        ):

            error = (
                "Invalid username or password."
            )

        else:

            session.clear()

            session["admin_id"] = admin.id

            session["admin_username"] = (
                admin.username
            )

            session["admin_name"] = (
                admin.display_name
            )

            session["admin_role"] = (
                admin.role
            )

            return redirect(
                url_for("admin.dashboard")
            )

    return render_template(
        "admin/login.html",
        error=error
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@bp.route("/logout")
@admin_login_required
def logout():

    session.clear()

    return redirect(
        url_for("admin.login")
    )

# ============================================================
# ADMIN DASHBOARD
# ============================================================

@bp.route("/")
@bp.route("/dashboard")
@admin_login_required
def dashboard():

    current_month_year = datetime.now().strftime("%B %Y")


    # ========================================================
    # TOTAL THESIS
    # ========================================================

    total_theses = (
        Thesis.query
        .filter(
            Thesis.is_archived.is_(False)
        )
        .count()
    )


    # ========================================================
    # AVAILABLE THESIS
    # ========================================================

    available_theses = (
        Thesis.query
        .filter(
            Thesis.is_archived.is_(False),
            Thesis.availability == "Available"
        )
        .count()
    )


    # ========================================================
    # BORROWED THESIS
    # ========================================================

    borrowed_theses = (
        Thesis.query
        .filter(
            Thesis.is_archived.is_(False),
            Thesis.availability == "Borrowed"
        )
        .count()
    )


    # ========================================================
    # TOTAL BORROWING REQUESTS
    # ========================================================

    total_requests = (
        BorrowingRequest.query
        .count()
    )


    # ========================================================
    # CURRENT REQUESTED / PENDING
    # ========================================================

    requested_count = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.status == "Requested"
        )
        .count()
    )


    # ========================================================
    # ACTIVE BORROWINGS
    # ========================================================

    active_borrowings = (
        Transaction.query
        .filter(
            Transaction.status == "Borrowed"
        )
        .count()
    )


    # ========================================================
    # RETURNED TRANSACTIONS
    # ========================================================

    total_returned = (
        Transaction.query
        .filter(
            Transaction.status == "Returned"
        )
        .count()
    )


    # ========================================================
    # TOTAL SEARCHES
    # ========================================================

    total_searches = (
        SearchLog.query
        .count()
    )


    # ========================================================
    # TOP BORROWED THESIS RANKING
    #
    # Counts all recorded borrowing transactions,
    # including current Borrowed and completed Returned.
    # ========================================================

    most_borrowed_theses = (
        db.session.query(

            Thesis.id.label(
                "thesis_id"
            ),

            Thesis.title.label(
                "title"
            ),

            func.count(
                Transaction.id
            ).label(
                "borrow_count"
            )

        )
        .join(
            Transaction,
            Transaction.thesis_id == Thesis.id
        )
        .filter(
            Thesis.is_archived.is_(False),
            Transaction.status.in_(
                [
                    "Borrowed",
                    "Returned"
                ]
            )
        )
        .group_by(
            Thesis.id,
            Thesis.title
        )
        .order_by(
            func.count(
                Transaction.id
            ).desc(),
            Thesis.title.asc()
        )
        .limit(5)
        .all()
    )


    # ========================================================
    # RECENT BORROWING REQUESTS
    # ========================================================

    recent_requests = (
        BorrowingRequest.query
        .order_by(
            BorrowingRequest.request_date.desc(),
            BorrowingRequest.id.desc()
        )
        .limit(6)
        .all()
    )


    # ========================================================
    # POPULAR SEARCHES
    # ========================================================

    most_searched_terms = (
        db.session.query(

            SearchLog.normalized_query,

            func.count(
                SearchLog.id
            ).label(
                "search_count"
            )

        )
        .filter(
            SearchLog.normalized_query.isnot(None),
            SearchLog.normalized_query != ""
        )
        .group_by(
            SearchLog.normalized_query
        )
        .order_by(
            func.count(
                SearchLog.id
            ).desc(),
            SearchLog.normalized_query.asc()
        )
        .limit(6)
        .all()
    )


    # ========================================================
    # MAX SEARCH COUNT
    # Used by the progress bars in dashboard.html
    # ========================================================

    max_search_count = 1

    if most_searched_terms:

        max_search_count = max(
            item.search_count
            for item in most_searched_terms
        )


    # ========================================================
    # RENDER DASHBOARD
    # ========================================================

    return render_template(

        "admin/dashboard.html",

        current_month_year=
            current_month_year,

        total_theses=
            total_theses,

        available_theses=
            available_theses,

        borrowed_theses=
            borrowed_theses,

        total_requests=
            total_requests,

        requested_count=
            requested_count,

        active_borrowings=
            active_borrowings,

        total_returned=
            total_returned,

        total_searches=
            total_searches,

        most_borrowed_theses=
            most_borrowed_theses,

        recent_requests=
            recent_requests,

        most_searched_terms=
            most_searched_terms,

        max_search_count=
            max_search_count,
    )

# ============================================================
# THESIS MANAGEMENT
# ============================================================

@bp.route("/theses")
@admin_login_required
def thesis_management():

    # ========================================================
    # FILTER VALUES
    # ========================================================

    search_text = request.args.get(
        "q",
        ""
    ).strip()

    academic_level_id = request.args.get(
        "level",
        "",
        type=str
    )

    department_id = request.args.get(
        "department",
        "",
        type=str
    )

    program_id = request.args.get(
        "program",
        "",
        type=str
    )

    year_published = request.args.get(
        "year",
        "",
        type=str
    )

    availability = request.args.get(
        "availability",
        ""
    )

    page = request.args.get(
        "page",
        1,
        type=int
    )


    # ========================================================
    # BASE QUERY
    # ========================================================

    thesis_query = (
        Thesis.query
        .join(
            Program,
            Thesis.program_id == Program.id
        )
        .join(
            Department,
            Program.department_id == Department.id
        )
        .join(
            AcademicLevel,
            Program.academic_level_id == AcademicLevel.id
        )
        .filter(
            Thesis.is_archived.is_(False)
        )
    )


    # ========================================================
    # SEARCH
    # ========================================================

    if search_text:

        pattern = (
            f"%{search_text}%"
        )

        thesis_query = thesis_query.filter(
            or_(
                Thesis.thesis_code.ilike(pattern),
                Thesis.title.ilike(pattern),
                Thesis.author_researchers.ilike(pattern),
                Thesis.research_field.ilike(pattern),
                Thesis.research_topic.ilike(pattern),
                Thesis.keywords.ilike(pattern),
                Thesis.shelf_location.ilike(pattern),
                Program.program_name.ilike(pattern),
                Department.department_college.ilike(pattern),
            )
        )


    # ========================================================
    # ACADEMIC LEVEL FILTER
    # ========================================================

    if academic_level_id:

        try:

            thesis_query = thesis_query.filter(
                AcademicLevel.id
                == int(academic_level_id)
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # DEPARTMENT FILTER
    # ========================================================

    if department_id:

        try:

            thesis_query = thesis_query.filter(
                Department.id
                == int(department_id)
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # PROGRAM FILTER
    # ========================================================

    if program_id:

        try:

            thesis_query = thesis_query.filter(
                Program.id
                == int(program_id)
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # YEAR FILTER
    # ========================================================

    if year_published:

        try:

            thesis_query = thesis_query.filter(
                Thesis.year_published
                == int(year_published)
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # AVAILABILITY FILTER
    # ========================================================

    if availability in [
        "Available",
        "Borrowed",
    ]:

        thesis_query = thesis_query.filter(
            Thesis.availability
            == availability
        )


    # ========================================================
    # ORDER + PAGINATION
    # ========================================================

    pagination = (
        thesis_query
        .order_by(
            Thesis.year_published.desc(),
            Thesis.title.asc()
        )
        .paginate(
            page=page,
            per_page=20,
            error_out=False
        )
    )


    theses = pagination.items


    # ========================================================
    # FILTER OPTIONS
    # ========================================================

    academic_levels = (
        AcademicLevel.query
        .order_by(
            AcademicLevel.id
        )
        .all()
    )


    departments = (
        Department.query
        .order_by(
            Department.department_college.asc()
        )
        .all()
    )


    programs = (
        Program.query
        .filter(
            Program.is_active.is_(True)
        )
        .order_by(
            Program.program_name.asc()
        )
        .all()
    )


    years = (
        db.session.query(
            Thesis.year_published
        )
        .filter(
            Thesis.is_archived.is_(False)
        )
        .distinct()
        .order_by(
            Thesis.year_published.desc()
        )
        .all()
    )


    return render_template(
        "admin/thesis_management.html",

        theses=theses,

        pagination=pagination,

        search_text=search_text,

        selected_level=
            academic_level_id,

        selected_department=
            department_id,

        selected_program=
            program_id,

        selected_year=
            year_published,

        selected_availability=
            availability,

        academic_levels=
            academic_levels,

        departments=
            departments,

        programs=
            programs,

        years=[
            row[0]
            for row in years
        ],
    )


# ============================================================
# ADD THESIS
# ============================================================

@bp.route(
    "/theses/add",
    methods=["GET", "POST"]
)
@admin_login_required
def add_thesis():

    academic_levels = (
        AcademicLevel.query
        .order_by(
            AcademicLevel.id
        )
        .all()
    )


    departments = (
        Department.query
        .order_by(
            Department.department_college.asc()
        )
        .all()
    )


    programs = (
        Program.query
        .filter(
            Program.is_active.is_(True)
        )
        .order_by(
            Program.program_name.asc()
        )
        .all()
    )


    errors = []


    if request.method == "POST":

        thesis_code = request.form.get(
            "thesis_code",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        author_researchers = request.form.get(
            "author_researchers",
            ""
        ).strip()

        program_id = request.form.get(
            "program_id",
            type=int
        )

        year_published = request.form.get(
            "year_published",
            type=int
        )

        abstract = request.form.get(
            "abstract",
            ""
        ).strip()

        keywords = request.form.get(
            "keywords",
            ""
        ).strip()

        research_field = request.form.get(
            "research_field",
            ""
        ).strip()

        research_topic = request.form.get(
            "research_topic",
            ""
        ).strip()

        research_subtopic = request.form.get(
            "research_subtopic",
            ""
        ).strip()

        shelf_location = request.form.get(
            "shelf_location",
            ""
        ).strip()

        availability = request.form.get(
            "availability",
            "Available"
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not thesis_code:

            errors.append(
                "Thesis code is required."
            )


        if not title:

            errors.append(
                "Thesis title is required."
            )


        if not author_researchers:

            errors.append(
                "Author / researchers are required."
            )


        if not program_id:

            errors.append(
                "Program / course is required."
            )


        if not year_published:

            errors.append(
                "Year published is required."
            )


        if not abstract:

            errors.append(
                "Abstract is required."
            )


        if not keywords:

            errors.append(
                "Keywords are required."
            )


        if not research_field:

            errors.append(
                "Research field is required."
            )


        if not research_topic:

            errors.append(
                "Research topic is required."
            )


        if not shelf_location:

            errors.append(
                "Shelf location is required."
            )


        if availability not in [
            "Available",
            "Borrowed",
        ]:

            errors.append(
                "Invalid availability value."
            )


        # ====================================================
        # UNIQUE THESIS CODE
        # ====================================================

        existing_code = (
            Thesis.query
            .filter(
                func.lower(
                    Thesis.thesis_code
                )
                == thesis_code.lower()
            )
            .first()
        )


        if existing_code:

            errors.append(
                "Thesis code already exists."
            )


        # ====================================================
        # PROGRAM CHECK
        # ====================================================

        program = None

        if program_id:

            program = db.session.get(
                Program,
                program_id
            )

            if not program:

                errors.append(
                    "Selected program does not exist."
                )


        # ====================================================
        # YEAR CHECK
        # ====================================================

        current_year = datetime.now().year

        if year_published:

            if (
                year_published < 1900
                or
                year_published > current_year
            ):

                errors.append(
                    "Please enter a valid year published."
                )


        # ====================================================
        # SAVE
        # ====================================================

        if not errors:

            thesis = Thesis(

                thesis_code=
                    thesis_code,

                title=
                    title,

                author_researchers=
                    author_researchers,

                program_id=
                    program_id,

                year_published=
                    year_published,

                abstract=
                    abstract,

                keywords=
                    keywords,

                research_field=
                    research_field,

                research_topic=
                    research_topic,

                research_subtopic=
                    (
                        research_subtopic
                        if research_subtopic
                        else None
                    ),

                shelf_location=
                    shelf_location,

                availability=
                    availability,

                is_archived=
                    False,
            )


            db.session.add(
                thesis
            )

            db.session.commit()


            flash(
                "Thesis record added successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "admin.thesis_management"
                )
            )


    return render_template(
        "admin/thesis_form.html",

        mode="add",

        thesis=None,

        academic_levels=
            academic_levels,

        departments=
            departments,

        programs=
            programs,

        errors=
            errors,
    )


# ============================================================
# EDIT THESIS
# ============================================================

@bp.route(
    "/theses/<int:thesis_id>/edit",
    methods=["GET", "POST"]
)
@admin_login_required
def edit_thesis(thesis_id):

    thesis = (
        Thesis.query
        .filter(
            Thesis.id == thesis_id,
            Thesis.is_archived.is_(False)
        )
        .first_or_404()
    )


    academic_levels = (
        AcademicLevel.query
        .order_by(
            AcademicLevel.id
        )
        .all()
    )


    departments = (
        Department.query
        .order_by(
            Department.department_college.asc()
        )
        .all()
    )


    programs = (
        Program.query
        .filter(
            Program.is_active.is_(True)
        )
        .order_by(
            Program.program_name.asc()
        )
        .all()
    )


    errors = []


    if request.method == "POST":

        thesis_code = request.form.get(
            "thesis_code",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        author_researchers = request.form.get(
            "author_researchers",
            ""
        ).strip()

        program_id = request.form.get(
            "program_id",
            type=int
        )

        year_published = request.form.get(
            "year_published",
            type=int
        )

        abstract = request.form.get(
            "abstract",
            ""
        ).strip()

        keywords = request.form.get(
            "keywords",
            ""
        ).strip()

        research_field = request.form.get(
            "research_field",
            ""
        ).strip()

        research_topic = request.form.get(
            "research_topic",
            ""
        ).strip()

        research_subtopic = request.form.get(
            "research_subtopic",
            ""
        ).strip()

        shelf_location = request.form.get(
            "shelf_location",
            ""
        ).strip()

        availability = request.form.get(
            "availability",
            "Available"
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not thesis_code:
            errors.append(
                "Thesis code is required."
            )


        if not title:
            errors.append(
                "Thesis title is required."
            )


        if not author_researchers:
            errors.append(
                "Author / researchers are required."
            )


        if not program_id:
            errors.append(
                "Program / course is required."
            )


        if not year_published:
            errors.append(
                "Year published is required."
            )


        if not abstract:
            errors.append(
                "Abstract is required."
            )


        if not keywords:
            errors.append(
                "Keywords are required."
            )


        if not research_field:
            errors.append(
                "Research field is required."
            )


        if not research_topic:
            errors.append(
                "Research topic is required."
            )


        if not shelf_location:
            errors.append(
                "Shelf location is required."
            )


        if availability not in [
            "Available",
            "Borrowed",
        ]:

            errors.append(
                "Invalid availability value."
            )


        # ====================================================
        # DUPLICATE CODE CHECK
        # ====================================================

        duplicate_code = (
            Thesis.query
            .filter(
                Thesis.id != thesis.id,
                func.lower(
                    Thesis.thesis_code
                )
                == thesis_code.lower()
            )
            .first()
        )


        if duplicate_code:

            errors.append(
                "Another thesis already uses this thesis code."
            )


        # ====================================================
        # PROGRAM CHECK
        # ====================================================

        if program_id:

            program = db.session.get(
                Program,
                program_id
            )

            if not program:

                errors.append(
                    "Selected program does not exist."
                )


        # ====================================================
        # YEAR CHECK
        # ====================================================

        current_year = datetime.now().year

        if year_published:

            if (
                year_published < 1900
                or
                year_published > current_year
            ):

                errors.append(
                    "Please enter a valid year published."
                )


        # ====================================================
        # UPDATE
        # ====================================================

        if not errors:

            thesis.thesis_code = (
                thesis_code
            )

            thesis.title = (
                title
            )

            thesis.author_researchers = (
                author_researchers
            )

            thesis.program_id = (
                program_id
            )

            thesis.year_published = (
                year_published
            )

            thesis.abstract = (
                abstract
            )

            thesis.keywords = (
                keywords
            )

            thesis.research_field = (
                research_field
            )

            thesis.research_topic = (
                research_topic
            )

            thesis.research_subtopic = (
                research_subtopic
                if research_subtopic
                else None
            )

            thesis.shelf_location = (
                shelf_location
            )

            thesis.availability = (
                availability
            )


            db.session.commit()


            flash(
                "Thesis record updated successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "admin.thesis_management"
                )
            )


    return render_template(
        "admin/thesis_form.html",

        mode="edit",

        thesis=
            thesis,

        academic_levels=
            academic_levels,

        departments=
            departments,

        programs=
            programs,

        errors=
            errors,
    )


# ============================================================
# ARCHIVE THESIS
# ============================================================

@bp.route(
    "/theses/<int:thesis_id>/archive",
    methods=["POST"]
)
@admin_login_required
def archive_thesis(thesis_id):

    thesis = (
        Thesis.query
        .filter(
            Thesis.id == thesis_id,
            Thesis.is_archived.is_(False)
        )
        .first_or_404()
    )


    # ========================================================
    # DON'T ARCHIVE CURRENTLY BORROWED THESIS
    # ========================================================

    if thesis.availability == "Borrowed":

        flash(
            "A borrowed thesis cannot be archived until it is returned.",
            "error"
        )

        return redirect(
            url_for(
                "admin.thesis_management"
            )
        )


    thesis.is_archived = True

    db.session.commit()


    flash(
        "Thesis record archived successfully.",
        "success"
    )


    return redirect(
        url_for(
            "admin.thesis_management"
        )
    )

# ============================================================
# BORROWING REQUESTS
# ============================================================

@bp.route("/borrowing-requests")
@admin_login_required
def borrowing_requests():

    # ========================================================
    # FILTER
    # ========================================================

    selected_status = request.args.get(
        "status",
        ""
    ).strip()


    # ========================================================
    # BASE QUERY
    # ========================================================

    borrowing_query = (
        BorrowingRequest.query
        .join(
            Thesis,
            BorrowingRequest.thesis_id == Thesis.id
        )
    )


    # ========================================================
    # STATUS FILTER
    # ========================================================

    if selected_status in [
        "Requested",
        "Borrowed",
        "Returned",
    ]:

        borrowing_query = borrowing_query.filter(
            BorrowingRequest.status == selected_status
        )


    # ========================================================
    # ORDER
    # Latest request first
    # ========================================================

    requests_list = (
        borrowing_query
        .order_by(
            BorrowingRequest.request_date.desc(),
            BorrowingRequest.id.desc()
        )
        .all()
    )


    # ========================================================
    # REQUESTED COUNT
    # Used for sidebar badge
    # ========================================================

    requested_count = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.status == "Requested"
        )
        .count()
    )


    return render_template(
        "admin/borrowing_requests.html",

        requests_list=
            requests_list,

        selected_status=
            selected_status,

        requested_count=
            requested_count,
    )


# ============================================================
# BORROWING REQUEST DETAILS
# ============================================================

@bp.route(
    "/borrowing-requests/<int:request_id>"
)
@admin_login_required
def borrowing_request_details(request_id):

    borrowing_request = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.id == request_id
        )
        .first_or_404()
    )


    requested_count = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.status == "Requested"
        )
        .count()
    )


    return render_template(
        "admin/borrowing_request_details.html",

        borrowing_request=
            borrowing_request,

        requested_count=
            requested_count,
    )

# ============================================================
# DOWNLOAD BORROWING SLIP
# FINAL PROFESSIONAL SCHOOL-STYLE PDF
# ============================================================

@bp.route("/borrowing-requests/<int:request_id>/slip")
@admin_login_required
def borrowing_slip(request_id):

    # ========================================================
    # GET DATABASE RECORDS
    # ========================================================

    borrowing_request = (
        BorrowingRequest.query
        .filter(BorrowingRequest.id == request_id)
        .first_or_404()
    )

    thesis = borrowing_request.thesis

    academic_level = (
        db.session.get(
            AcademicLevel,
            borrowing_request.academic_level_id
        )
        if borrowing_request.academic_level_id
        else None
    )

    department = (
        db.session.get(
            Department,
            borrowing_request.department_id
        )
        if borrowing_request.department_id
        else None
    )

    program = (
        db.session.get(
            Program,
            borrowing_request.program_id
        )
        if borrowing_request.program_id
        else None
    )


    # ========================================================
    # SAFE VALUE HELPERS
    # ========================================================

    def safe(value):

        if value is None:
            return "N/A"

        value = str(value).strip()

        return value if value else "N/A"


    def format_datetime(value):

        if not value:
            return "N/A"

        try:
            return value.strftime(
                "%b %d, %Y - %I:%M %p"
            )

        except Exception:
            return safe(value)


    academic_level_name = (
        safe(
            getattr(
                academic_level,
                "academic_level",
                None
            )
        )
        if academic_level
        else "N/A"
    )

    department_name = (
        safe(
            getattr(
                department,
                "department_college",
                None
            )
        )
        if department
        else "N/A"
    )

    program_name = (
        safe(
            getattr(
                program,
                "program_name",
                None
            )
        )
        if program
        else "N/A"
    )


    # ========================================================
    # PDF SETUP
    # 8.5 x 6.5 inches
    # ========================================================

    PAGE_WIDTH = 8.5 * inch
    PAGE_HEIGHT = 6.5 * inch

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        leftMargin=7 * mm,
        rightMargin=7 * mm,
        topMargin=4 * mm,
        bottomMargin=4 * mm,
        title="LIBRA Thesis Borrowing Slip",
        author="Isabela State University - Echague Campus Library",
    )


    # ========================================================
    # STYLES
    # ========================================================

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SlipTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16.5,
        leading=17.0,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=0,
    )

    university_style = ParagraphStyle(
        "University",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=13.5,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=0,
    )

    campus_style = ParagraphStyle(
        "Campus",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=9.4,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=0,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=6.8,
        leading=6.8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
        spaceAfter=0,
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.3,
        leading=8.9,
        textColor=colors.black,
        alignment=TA_LEFT,
    )

    label_style = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.3,
        leading=5.2,
        textColor=colors.HexColor("#333333"),
    )

    value_style = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=8.2,
        textColor=colors.black,
    )

    value_bold_style = ParagraphStyle(
        "FieldValueBold",
        parent=value_style,
        fontName="Helvetica-Bold",
    )

    reminder_style = ParagraphStyle(
        "Reminder",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.7,
        leading=8.2,
        textColor=colors.black,
    )

    signature_label_style = ParagraphStyle(
        "SignatureLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=6.8,
        alignment=TA_CENTER,
        textColor=colors.black,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.0,
        leading=5.2,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#777777"),
    )

    footer_italic_style = ParagraphStyle(
        "FooterItalic",
        parent=footer_style,
        fontName="Helvetica-Oblique",
    )


    # ========================================================
    # LOGO HELPER
    # ========================================================

    def logo_flowable(filename, width_mm, height_mm):

        path = os.path.join(
            current_app.static_folder,
            "img",
            filename
        )

        if not os.path.exists(path):
            return Spacer(
                width_mm * mm,
                height_mm * mm
            )

        try:

            image = RLImage(
                path,
                width=width_mm * mm,
                height=height_mm * mm
            )

            image.hAlign = "CENTER"

            return image

        except Exception:

            return Spacer(
                width_mm * mm,
                height_mm * mm
            )


    # ========================================================
    # SMALL HELPERS
    # ========================================================

    def P(text, style=value_style):
        return Paragraph(
            safe(text),
            style
        )


    def field_block(label, value, bold=False):

        label_paragraph = Paragraph(
            safe(label).upper(),
            label_style
        )

        value_paragraph = Paragraph(
            safe(value),
            value_bold_style if bold else value_style
        )

        return [
            label_paragraph,
            value_paragraph
        ]


    def section_bar(title):

        table = Table(
            [[Paragraph(title.upper(), section_style)]],
            colWidths=[doc.width],
            rowHeights=[5.8 * mm]
        )

        table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F1F1F1")
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2.2 * mm
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2 * mm
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
            ])
        )

        return table


    def two_column_fields(rows):

        data = []

        for left_item, right_item in rows:

            left_label, left_value = left_item
            right_label, right_value = right_item

            data.append([
                Paragraph(
                    safe(left_label).upper(),
                    label_style
                ),
                Paragraph(
                    safe(left_value),
                    value_style
                ),
                Paragraph(
                    safe(right_label).upper(),
                    label_style
                ),
                Paragraph(
                    safe(right_value),
                    value_style
                ),
            ])

        table = Table(
            data,
            colWidths=[
                29 * mm,
                66 * mm,
                29 * mm,
                66 * mm,
            ],
            rowHeights=None,
            hAlign="LEFT"
        )

        table.setStyle(
            TableStyle([
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2 * mm
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2 * mm
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.15 * mm
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.15 * mm
                ),
                (
                    "LINEBEFORE",
                    (2, 0),
                    (2, -1),
                    0.35,
                    colors.HexColor("#B7B7B7")
                ),
            ])
        )

        return table


    # ========================================================
    # STORY
    # ========================================================

    story = []


    # ========================================================
    # HEADER
    # ========================================================

    header_center = [
        Paragraph(
            "ISABELA STATE UNIVERSITY",
            university_style
        ),
        Paragraph(
            "ECHAGUE CAMPUS LIBRARY",
            campus_style
        ),
        Spacer(1, 1.0 * mm),
        Paragraph(
            "LIBRA THESIS BORROWING SLIP",
            title_style
        ),
        Paragraph(
            "Library Integrated Borrowing, Research, and Analytics",
            subtitle_style
        ),
    ]

    header_table = Table(
        [[
            logo_flowable(
                "libra_logo.png",
                24,
                24
            ),
            header_center,
            logo_flowable(
                "isu_logo.png",
                24,
                24
            )
        ]],
        colWidths=[
            34 * mm,
            doc.width - (68 * mm),
            34 * mm,
        ],
        rowHeights=[27 * mm]
    )

    header_table.setStyle(
        TableStyle([
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
        ])
    )

    story.append(header_table)

    story.append(
        Table(
            [[""]],
            colWidths=[doc.width],
            rowHeights=[0.6 * mm],
            style=[
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.black
                )
            ]
        )
    )

    story.append(
        Spacer(1, 1.8 * mm)
    )


    # ========================================================
    # REQUEST INFORMATION
    # ========================================================

    story.append(
        section_bar(
            "Request Information"
        )
    )

    story.append(
        two_column_fields([
            (
                (
                    "Request ID",
                    borrowing_request.request_id
                ),
                (
                    "Request Status",
                    borrowing_request.status
                )
            ),
            (
                (
                    "Request Date",
                    format_datetime(
                        borrowing_request.request_date
                    )
                ),
                (
                    "Borrower Type",
                    borrowing_request.user_type
                )
            ),
        ])
    )


    # ========================================================
    # BORROWER INFORMATION
    # ========================================================

    story.append(
        section_bar(
            "Borrower Information"
        )
    )

    story.append(
        two_column_fields([
            (
                (
                    "Full Name",
                    borrowing_request.full_name
                ),
                (
                    "Gender / Age",
                    (
                        f"{safe(borrowing_request.gender)}"
                        f" / "
                        f"{safe(borrowing_request.age)} years old"
                    )
                )
            ),
            (
                (
                    "Year Level",
                    borrowing_request.year_level
                ),
                (
                    "Address",
                    borrowing_request.address
                )
            ),
        ])
    )


    # ========================================================
    # ACADEMIC INFORMATION
    # ========================================================

    story.append(
        section_bar(
            "Academic Information"
        )
    )

    story.append(
        two_column_fields([
            (
                (
                    "Academic Level",
                    academic_level_name
                ),
                (
                    "Course / Program",
                    program_name
                )
            ),
            (
                (
                    "Department / College",
                    department_name
                ),
                (
                    "Year Level",
                    borrowing_request.year_level
                )
            ),
        ])
    )


    # ========================================================
    # RESEARCH MATERIAL
    # ========================================================

    story.append(
        section_bar(
            "Research Material"
        )
    )

    research_table = Table(
        [
            [
                Paragraph(
                    "THESIS TITLE",
                    label_style
                ),
                Paragraph(
                    safe(thesis.title),
                    value_style
                ),
                "",
                "",
            ],
            [
                Paragraph(
                    "THESIS CODE",
                    label_style
                ),
                Paragraph(
                    safe(thesis.thesis_code),
                    value_style
                ),
                Paragraph(
                    "YEAR PUBLISHED",
                    label_style
                ),
                Paragraph(
                    safe(thesis.year_published),
                    value_style
                ),
            ],
            [
                Paragraph(
                    "AUTHOR / RESEARCHERS",
                    label_style
                ),
                Paragraph(
                    safe(thesis.author_researchers),
                    value_style
                ),
                Paragraph(
                    "SHELF / LOCATION",
                    label_style
                ),
                Paragraph(
                    safe(thesis.shelf_location),
                    value_style
                ),
            ],
        ],
        colWidths=[
            29 * mm,
            66 * mm,
            29 * mm,
            66 * mm,
        ]
    )

    research_table.setStyle(
        TableStyle([
            (
                "SPAN",
                (1, 0),
                (3, 0)
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2 * mm
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                2 * mm
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                1.15 * mm
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                1.15 * mm
            ),
            (
                "LINEBEFORE",
                (2, 1),
                (2, -1),
                0.35,
                colors.HexColor("#B7B7B7")
            ),
        ])
    )

    story.append(
        research_table
    )


    # ========================================================
    # BORROWING DETAILS
    # ========================================================

    duration_text = "N/A"

    if borrowing_request.duration_hours:

        try:

            hours = float(
                borrowing_request.duration_hours
            )

            if hours.is_integer():
                hours = int(hours)

            duration_text = (
                f"{hours} hour(s)"
            )

        except Exception:

            duration_text = (
                f"{safe(borrowing_request.duration_hours)} hour(s)"
            )


    story.append(
        section_bar(
            "Borrowing Details"
        )
    )

    story.append(
        two_column_fields([
            (
                (
                    "Borrowing Time",
                    format_datetime(
                        borrowing_request.requested_borrowing_time
                    )
                ),
                (
                    "Expected Return",
                    format_datetime(
                        borrowing_request.expected_return_time
                    )
                )
            ),
            (
                (
                    "Borrowing Duration",
                    duration_text
                ),
                (
                    "Borrowing Location",
                    borrowing_request.borrowing_location
                )
            ),
        ])
    )


    # ========================================================
    # IMPORTANT REMINDERS
    # ========================================================

    reminder_box = Table(
        [
            [
                Paragraph(
                    "IMPORTANT REMINDERS",
                    section_style
                ),
                ""
            ],
            [
                Paragraph(
                    "• Handle the research material carefully.<br/>"
                    "• Observe the approved borrowing duration and location.",
                    reminder_style
                ),
                Paragraph(
                    "• Return the material on or before the expected return time.<br/>"
                    "• Borrowed / Returned status is recorded by the librarian.",
                    reminder_style
                ),
            ]
        ],
        colWidths=[
            doc.width / 2,
            doc.width / 2
        ]
    )

    reminder_box.setStyle(
        TableStyle([
            (
                "SPAN",
                (0, 0),
                (1, 0)
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.45,
                colors.HexColor("#A0A0A0")
            ),
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#F7F7F7")
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                3 * mm
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                3 * mm
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                1.2 * mm
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                1.2 * mm
            ),
        ])
    )

    story.append(
        Spacer(1, 1.2 * mm)
    )

    story.append(
        reminder_box
    )


    # ========================================================
    # LOCATION NOTE
    # ========================================================

    story.append(
        Spacer(1, 1.2 * mm)
    )

    story.append(
        Paragraph(
            f"<b>{safe(borrowing_request.borrowing_location)}</b>",
            ParagraphStyle(
                "LocationNote",
                parent=value_style,
                fontName="Helvetica-Bold",
                fontSize=7.7,
                leading=8,
                alignment=TA_CENTER,
            )
        )
    )


    # ========================================================
    # SIGNATURES
    # ========================================================

    signature_table = Table(
        [
            [
                "_______________________________",
                "_______________________________"
            ],
            [
                Paragraph(
                    "BORROWER'S SIGNATURE",
                    signature_label_style
                ),
                Paragraph(
                    "LIBRARIAN'S SIGNATURE",
                    signature_label_style
                ),
            ],
            [
                Paragraph(
                    "Date: ____________________",
                    ParagraphStyle(
                        "DateLeft",
                        parent=footer_style,
                        fontSize=5.8,
                        alignment=TA_CENTER,
                        textColor=colors.black
                    )
                ),
                Paragraph(
                    "Date: ____________________",
                    ParagraphStyle(
                        "DateRight",
                        parent=footer_style,
                        fontSize=5.8,
                        alignment=TA_CENTER,
                        textColor=colors.black
                    )
                ),
            ]
        ],
        colWidths=[
            doc.width / 2,
            doc.width / 2
        ]
    )

    signature_table.setStyle(
        TableStyle([
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                1.2 * mm
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                1.2 * mm
            ),
        ])
    )

    story.append(
        Spacer(1, 1.2 * mm)
    )

    story.append(
        Spacer(1, 2.0 * mm)
    )

    story.append(
        signature_table
    )


    # ========================================================
    # FOOTER
    # ========================================================

    footer = Table(
        [
            [
                Paragraph(
                    (
                        "Generated through LIBRA | "
                        "Isabela State University - Echague Campus Library"
                    ),
                    footer_style
                )
            ],
            [
                Paragraph(
                    "Official library borrowing record.",
                    footer_italic_style
                )
            ]
        ],
        colWidths=[doc.width]
    )

    footer.setStyle(
        TableStyle([
            (
                "LINEABOVE",
                (0, 0),
                (-1, 0),
                0.35,
                colors.HexColor("#A0A0A0")
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0.5 * mm
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
        ])
    )

    story.append(
        Spacer(1, 1.0 * mm)
    )

    story.append(
        footer
    )


    # ========================================================
    # PAGE BORDER CALLBACK
    # ========================================================

    def draw_page_border(canvas_obj, doc_obj):

        canvas_obj.saveState()

        canvas_obj.setStrokeColor(
            colors.black
        )

        canvas_obj.setLineWidth(
            0.7
        )

        canvas_obj.rect(
            6 * mm,
            6 * mm,
            PAGE_WIDTH - (12 * mm),
            PAGE_HEIGHT - (12 * mm)
        )

        canvas_obj.restoreState()


    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        story,
        onFirstPage=draw_page_border,
        onLaterPages=draw_page_border
    )

    buffer.seek(0)


    filename = (
        f"LIBRA_Borrowing_Slip_"
        f"{safe(borrowing_request.request_id)}"
        f".pdf"
    )


    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )



# ============================================================
# TRANSACTIONS
# ============================================================

@bp.route("/transactions")
@admin_login_required
def transactions():

    selected_status = request.args.get(
        "status",
        ""
    ).strip()

    search_text = request.args.get(
        "q",
        ""
    ).strip()

    transaction_query = (
        Transaction.query
        .join(
            BorrowingRequest,
            Transaction.borrowing_request_id
            == BorrowingRequest.id
        )
        .join(
            Thesis,
            Transaction.thesis_id
            == Thesis.id
        )
    )

    if selected_status in (
        "Borrowed",
        "Returned",
    ):
        transaction_query = (
            transaction_query.filter(
                Transaction.status
                == selected_status
            )
        )

    if search_text:

        pattern = f"%{search_text}%"

        transaction_query = (
            transaction_query.filter(
                or_(
                    Transaction.transaction_id.ilike(
                        pattern
                    ),
                    BorrowingRequest.request_id.ilike(
                        pattern
                    ),
                    BorrowingRequest.full_name.ilike(
                        pattern
                    ),
                    Thesis.thesis_code.ilike(
                        pattern
                    ),
                    Thesis.title.ilike(
                        pattern
                    ),
                )
            )
        )

    transactions_list = (
        transaction_query
        .order_by(
            Transaction.date_time_borrowed.desc(),
            Transaction.id.desc()
        )
        .all()
    )

    total_transactions = (
        Transaction.query.count()
    )

    active_count = (
        Transaction.query
        .filter(
            Transaction.status == "Borrowed"
        )
        .count()
    )

    returned_count = (
        Transaction.query
        .filter(
            Transaction.status == "Returned"
        )
        .count()
    )

    requested_count = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.status == "Requested"
        )
        .count()
    )

    return render_template(
        "admin/transactions.html",
        transactions_list=transactions_list,
        selected_status=selected_status,
        search_text=search_text,
        total_transactions=total_transactions,
        active_count=active_count,
        returned_count=returned_count,
        requested_count=requested_count,
    )


# ============================================================
# MARK BORROWING REQUEST AS BORROWED
# ============================================================

@bp.route(
    "/borrowing-requests/<int:request_id>/mark-borrowed",
    methods=["POST"]
)
@admin_login_required
def mark_as_borrowed(request_id):

    borrowing_request = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.id == request_id
        )
        .first_or_404()
    )

    thesis = borrowing_request.thesis

    if borrowing_request.status != "Requested":

        flash(
            "This borrowing request has already been processed.",
            "error"
        )

        return redirect(
            url_for(
                "admin.borrowing_request_details",
                request_id=borrowing_request.id
            )
        )

    existing_transaction = (
        Transaction.query
        .filter(
            Transaction.borrowing_request_id
            == borrowing_request.id
        )
        .first()
    )

    if existing_transaction:

        flash(
            "A transaction already exists for this request.",
            "error"
        )

        return redirect(
            url_for(
                "admin.borrowing_request_details",
                request_id=borrowing_request.id
            )
        )

    if thesis.availability != "Available":

        flash(
            "This thesis is currently unavailable.",
            "error"
        )

        return redirect(
            url_for(
                "admin.borrowing_request_details",
                request_id=borrowing_request.id
            )
        )

    transaction_code = (
        f"TX-{datetime.now().year}-"
        f"{uuid.uuid4().hex[:10].upper()}"
    )

    transaction = Transaction(
        transaction_id=transaction_code,
        borrowing_request_id=borrowing_request.id,
        thesis_id=thesis.id,
        date_time_borrowed=datetime.now(),
        expected_return_time=borrowing_request.expected_return_time,
        borrowing_location=borrowing_request.borrowing_location,
        actual_return_time=None,
        status="Borrowed",
    )

    borrowing_request.status = "Borrowed"
    thesis.availability = "Borrowed"

    try:

        db.session.add(transaction)
        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        flash(
            f"The transaction could not be created: {exc}",
            "error"
        )

        return redirect(
            url_for(
                "admin.borrowing_request_details",
                request_id=borrowing_request.id
            )
        )

    flash(
        "Thesis successfully marked as borrowed.",
        "success"
    )

    return redirect(
        url_for(
            "admin.borrowing_request_details",
            request_id=borrowing_request.id
        )
    )


# ============================================================
# MARK TRANSACTION AS RETURNED
# ============================================================

@bp.route(
    "/transactions/<int:transaction_id>/mark-returned",
    methods=["POST"]
)
@admin_login_required
def mark_as_returned(transaction_id):

    transaction = (
        Transaction.query
        .filter(
            Transaction.id == transaction_id
        )
        .first_or_404()
    )

    if transaction.status != "Borrowed":

        flash(
            "This transaction has already been completed.",
            "error"
        )

        return redirect(
            url_for("admin.transactions")
        )

    borrowing_request = (
        transaction.borrowing_request
    )

    thesis = (
        borrowing_request.thesis
    )

    transaction.status = "Returned"
    transaction.actual_return_time = datetime.now()

    borrowing_request.status = "Returned"

    thesis.availability = "Available"

    try:

        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        flash(
            f"The return transaction could not be completed: {exc}",
            "error"
        )

        return redirect(
            url_for("admin.transactions")
        )

    flash(
        "Thesis successfully marked as returned.",
        "success"
    )

    return redirect(
        url_for(
            "admin.transactions",
            status="Returned"
        )
    )


# ============================================================
# LIBRARY ANALYTICS
# ============================================================

@bp.route("/analytics")
@admin_login_required
def analytics():

    selected_month = request.args.get(
        "month",
        ""
    ).strip()

    selected_semester = request.args.get(
        "semester",
        ""
    ).strip()

    selected_school_year = request.args.get(
        "school_year",
        ""
    ).strip()

    requested_count = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.status == "Requested"
        )
        .count()
    )

    # --------------------------------------------------------
    # Date-filter helper
    # School year is treated as Aug 1 through Jul 31.
    # 1st semester: Aug-Dec
    # 2nd semester: Jan-May
    # --------------------------------------------------------

    def matches_time_filter(value):

        if value is None:
            return False

        if selected_school_year:

            try:
                sy_start_text, sy_end_text = (
                    selected_school_year.split(
                        "-",
                        1
                    )
                )

                sy_start = int(
                    sy_start_text
                )

                sy_end = int(
                    sy_end_text
                )

            except (ValueError, TypeError):

                sy_start = None
                sy_end = None

            if sy_start is not None:

                sy_start_date = datetime(
                    sy_start,
                    8,
                    1
                )

                sy_end_date = datetime(
                    sy_end,
                    7,
                    31,
                    23,
                    59,
                    59
                )

                if not (
                    sy_start_date
                    <= value
                    <= sy_end_date
                ):
                    return False

        if selected_semester == "1":

            if value.month not in (
                8,
                9,
                10,
                11,
                12,
            ):
                return False

        elif selected_semester == "2":

            if value.month not in (
                1,
                2,
                3,
                4,
                5,
            ):
                return False

        if selected_month:

            try:
                month_number = int(
                    selected_month
                )

            except ValueError:
                month_number = None

            if (
                month_number is not None
                and value.month != month_number
            ):
                return False

        return True

    has_time_filter = any(
        (
            selected_month,
            selected_semester,
            selected_school_year,
        )
    )

    # --------------------------------------------------------
    # Load activity records.
    # --------------------------------------------------------

    all_transactions = (
        Transaction.query
        .order_by(
            Transaction.date_time_borrowed.asc()
        )
        .all()
    )

    all_search_logs = (
        SearchLog.query
        .order_by(
            SearchLog.searched_at.asc()
        )
        .all()
    )

    all_requests = (
        BorrowingRequest.query
        .order_by(
            BorrowingRequest.request_date.asc()
        )
        .all()
    )

    if has_time_filter:

        filtered_transactions = [
            item
            for item in all_transactions
            if matches_time_filter(
                item.date_time_borrowed
            )
        ]

        filtered_search_logs = [
            item
            for item in all_search_logs
            if matches_time_filter(
                item.searched_at
            )
        ]

        filtered_requests = [
            item
            for item in all_requests
            if matches_time_filter(
                item.request_date
            )
        ]

    else:

        filtered_transactions = (
            all_transactions
        )

        filtered_search_logs = (
            all_search_logs
        )

        filtered_requests = (
            all_requests
        )

    # --------------------------------------------------------
    # Thesis collection KPIs are current-state values.
    # --------------------------------------------------------

    active_theses = (
        Thesis.query
        .filter(
            Thesis.is_archived.is_(False)
        )
        .all()
    )

    total_theses = len(
        active_theses
    )

    available_count = sum(
        1
        for item in active_theses
        if item.availability == "Available"
    )

    borrowed_theses_count = sum(
        1
        for item in active_theses
        if item.availability == "Borrowed"
    )

    # --------------------------------------------------------
    # Activity KPIs respect the selected period.
    # --------------------------------------------------------

    total_borrowings = len(
        filtered_transactions
    )

    active_borrowings = sum(
        1
        for item in filtered_transactions
        if item.status == "Borrowed"
    )

    returned_count = sum(
        1
        for item in filtered_transactions
        if item.status == "Returned"
    )

    pending_requests = sum(
        1
        for item in filtered_requests
        if item.status == "Requested"
    )

    total_searches = len(
        filtered_search_logs
    )

    # --------------------------------------------------------
    # Lookup maps.
    # --------------------------------------------------------

    program_map = {
        item.id: item.program_name
        for item in Program.query.all()
    }

    academic_level_map = {
        item.id: item.academic_level
        for item in AcademicLevel.query.all()
    }

    thesis_map = {
        item.id: item.title
        for item in Thesis.query.all()
    }

    # --------------------------------------------------------
    # Most searched terms.
    # --------------------------------------------------------

    search_term_counts = {}

    for item in filtered_search_logs:

        key = (
            item.normalized_query
            or ""
        ).strip()

        if not key:
            continue

        search_term_counts[key] = (
            search_term_counts.get(
                key,
                0
            )
            + 1
        )

    most_searched_terms = [
        type(
            "SearchTermRow",
            (),
            {
                "normalized_query": key,
                "search_count": value,
            }
        )()
        for key, value in sorted(
            search_term_counts.items(),
            key=lambda pair: (
                -pair[1],
                pair[0]
            )
        )[:10]
    ]

    # --------------------------------------------------------
    # Popular search topics.
    # --------------------------------------------------------

    topic_counts = {}

    for item in filtered_search_logs:

        key = (
            item.topic_bucket
            or ""
        ).strip()

        if not key:
            continue

        topic_counts[key] = (
            topic_counts.get(
                key,
                0
            )
            + 1
        )

    popular_topics = [
        type(
            "TopicRow",
            (),
            {
                "topic_bucket": key,
                "search_count": value,
            }
        )()
        for key, value in sorted(
            topic_counts.items(),
            key=lambda pair: (
                -pair[1],
                pair[0]
            )
        )[:8]
    ]

    # --------------------------------------------------------
    # Most borrowed theses.
    # --------------------------------------------------------

    thesis_borrow_counts = {}

    for item in filtered_transactions:

        thesis_borrow_counts[item.thesis_id] = (
            thesis_borrow_counts.get(
                item.thesis_id,
                0
            )
            + 1
        )

    most_borrowed_theses = [
        type(
            "BorrowedThesisRow",
            (),
            {
                "title": thesis_map.get(
                    thesis_id,
                    f"Thesis #{thesis_id}"
                ),
                "borrow_count": value,
            }
        )()
        for thesis_id, value in sorted(
            thesis_borrow_counts.items(),
            key=lambda pair: (
                -pair[1],
                pair[0]
            )
        )[:6]
    ]

    # --------------------------------------------------------
    # Most active programs based on borrowing requests linked
    # to transactions in the filtered period.
    # --------------------------------------------------------

    program_borrow_counts = {}

    for item in filtered_transactions:

        borrowing_request = (
            item.borrowing_request
        )

        if (
            borrowing_request is None
            or borrowing_request.program_id is None
        ):
            continue

        program_id = (
            borrowing_request.program_id
        )

        program_borrow_counts[program_id] = (
            program_borrow_counts.get(
                program_id,
                0
            )
            + 1
        )

    most_active_programs = [
        type(
            "ProgramRow",
            (),
            {
                "program_name": program_map.get(
                    program_id,
                    f"Program #{program_id}"
                ),
                "borrow_count": value,
            }
        )()
        for program_id, value in sorted(
            program_borrow_counts.items(),
            key=lambda pair: (
                -pair[1],
                pair[0]
            )
        )[:6]
    ]

    # --------------------------------------------------------
    # Search activity by academic level.
    # --------------------------------------------------------

    level_search_counts = {}

    for item in filtered_search_logs:

        if item.academic_level_id is None:
            continue

        level_id = (
            item.academic_level_id
        )

        level_search_counts[level_id] = (
            level_search_counts.get(
                level_id,
                0
            )
            + 1
        )

    search_by_level = [
        type(
            "AcademicLevelRow",
            (),
            {
                "academic_level": academic_level_map.get(
                    level_id,
                    f"Level #{level_id}"
                ),
                "search_count": value,
            }
        )()
        for level_id, value in sorted(
            level_search_counts.items(),
            key=lambda pair: (
                -pair[1],
                pair[0]
            )
        )
    ]

    # --------------------------------------------------------
    # Monthly trend.
    # --------------------------------------------------------

    monthly_borrow_dict = {}

    for item in filtered_transactions:

        if item.date_time_borrowed is None:
            continue

        month_key = (
            item.date_time_borrowed.strftime(
                "%Y-%m"
            )
        )

        monthly_borrow_dict[month_key] = (
            monthly_borrow_dict.get(
                month_key,
                0
            )
            + 1
        )

    monthly_search_dict = {}

    for item in filtered_search_logs:

        if item.searched_at is None:
            continue

        month_key = (
            item.searched_at.strftime(
                "%Y-%m"
            )
        )

        monthly_search_dict[month_key] = (
            monthly_search_dict.get(
                month_key,
                0
            )
            + 1
        )

    month_keys = sorted(
        set(
            monthly_borrow_dict.keys()
        )
        |
        set(
            monthly_search_dict.keys()
        )
    )

    monthly_labels = []

    monthly_borrow_values = []

    monthly_search_values = []

    for month_key in month_keys:

        readable_month = (
            datetime.strptime(
                month_key,
                "%Y-%m"
            ).strftime(
                "%b %Y"
            )
        )

        monthly_labels.append(
            readable_month
        )

        monthly_borrow_values.append(
            monthly_borrow_dict.get(
                month_key,
                0
            )
        )

        monthly_search_values.append(
            monthly_search_dict.get(
                month_key,
                0
            )
        )

    top_keyword = (
        most_searched_terms[0]
        if most_searched_terms
        else None
    )

    most_active_program = (
        most_active_programs[0]
        if most_active_programs
        else None
    )

    return render_template(
        "admin/analytics.html",
        requested_count=requested_count,
        selected_month=selected_month,
        selected_semester=selected_semester,
        selected_school_year=selected_school_year,
        total_theses=total_theses,
        available_count=available_count,
        borrowed_theses_count=borrowed_theses_count,
        total_borrowings=total_borrowings,
        active_borrowings=active_borrowings,
        returned_count=returned_count,
        pending_requests=pending_requests,
        total_searches=total_searches,
        most_searched_terms=most_searched_terms,
        popular_topics=popular_topics,
        most_borrowed_theses=most_borrowed_theses,
        most_active_programs=most_active_programs,
        search_by_level=search_by_level,
        monthly_labels=monthly_labels,
        monthly_borrow_values=monthly_borrow_values,
        monthly_search_values=monthly_search_values,
        top_keyword=top_keyword,
        most_active_program=most_active_program,
    )