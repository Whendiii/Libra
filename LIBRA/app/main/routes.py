import uuid
from datetime import datetime, timedelta

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
)

from sqlalchemy import func

from . import bp

from app import db

from app.models import (
    Thesis,
    SearchLog,
    BorrowingRequest,
    AcademicLevel,
    Program,
    Department,
)

from app.services.search_service import (
    normalize_query,
    build_thesis_search,
    get_autocomplete_suggestions,
    get_search_filter_options,
)

from app.services.recommendation_service import (
    get_related_theses,
)


# ============================================================
# HOME
# ============================================================

@bp.route("/")
def home():

    featured_research = (
        Thesis.query
        .filter(
            Thesis.is_archived.is_(False)
        )
        .order_by(
            (
                Thesis.availability == "Available"
            ).desc(),
            Thesis.year_published.desc(),
            Thesis.id.desc(),
        )
        .limit(6)
        .all()
    )


    most_searched_topics = (
        SearchLog.query
        .with_entities(
            SearchLog.topic_bucket,
            func.count(
                SearchLog.id
            ).label(
                "search_count"
            )
        )
        .filter(
            SearchLog.topic_bucket.isnot(None),
            SearchLog.topic_bucket != ""
        )
        .group_by(
            SearchLog.topic_bucket
        )
        .order_by(
            func.count(
                SearchLog.id
            ).desc()
        )
        .limit(5)
        .all()
    )


    popular_terms = (
        SearchLog.query
        .with_entities(
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
            ).desc()
        )
        .limit(7)
        .all()
    )


    return render_template(
        "home.html",
        featured_research=featured_research,
        most_searched_topics=most_searched_topics,
        popular_terms=popular_terms,
    )


# ============================================================
# SEARCH REDIRECT FROM HOME
# ============================================================

@bp.route("/search-submit")
def search_submit():

    query = request.args.get(
        "q",
        ""
    ).strip()

    return redirect(
        url_for(
            "main.search",
            q=query
        )
    )


# ============================================================
# SEARCH PAGE
# ============================================================

@bp.route("/search")
def search():

    query_text = request.args.get(
        "q",
        ""
    ).strip()

    academic_level = request.args.get(
        "level",
        ""
    )

    program_id = request.args.get(
        "program",
        ""
    )

    department_id = request.args.get(
        "department",
        ""
    )

    research_field = request.args.get(
        "field",
        ""
    )

    year_published = request.args.get(
        "year",
        ""
    )

    availability = request.args.get(
        "availability",
        ""
    )

    author = request.args.get(
        "author",
        ""
    ).strip()

    page = request.args.get(
        "page",
        1,
        type=int
    )


    # ========================================================
    # BUILD SEARCH QUERY
    # ========================================================

    thesis_query = build_thesis_search(
        query_text=query_text,
        academic_level=academic_level,
        program_id=program_id,
        department_id=department_id,
        research_field=research_field,
        year_published=year_published,
        availability=availability,
        author=author,
    )


    # ========================================================
    # PAGINATION
    # ========================================================

    pagination = (
        thesis_query
        .order_by(
            Thesis.year_published.desc(),
            Thesis.title.asc()
        )
        .paginate(
            page=page,
            per_page=12,
            error_out=False
        )
    )

    results = pagination.items


    # ========================================================
    # FILTER OPTIONS
    # ========================================================

    filter_options = (
        get_search_filter_options()
    )


    # ========================================================
    # RECORD SEARCH ACTIVITY
    # ========================================================

    has_search_activity = any([
        query_text,
        academic_level,
        program_id,
        department_id,
        research_field,
        year_published,
        availability,
        author,
    ])


    if has_search_activity:

        normalized = normalize_query(
            query_text
        )

        topic_bucket = (
            research_field
            or normalized.title()
            or None
        )

        # Resolve academic level code to ID
        academic_level_id = None

        if academic_level:

            level_record = (
                AcademicLevel.query
                .filter_by(
                    level_code=academic_level
                )
                .first()
            )

            if level_record:
                academic_level_id = level_record.id


        search_log = SearchLog(
            search_id=
                f"WEB-{uuid.uuid4().hex[:20]}",

            search_query=query_text,

            normalized_query=normalized,

            topic_bucket=topic_bucket,

            academic_level_id=
                academic_level_id,

            program_id=
                int(program_id)
                if program_id.isdigit()
                else None,

            research_field_filter=
                research_field or None,

            result_count=
                pagination.total,
        )


        db.session.add(
            search_log
        )

        db.session.commit()


    return render_template(
        "search.html",
        results=results,
        pagination=pagination,
        query=query_text,
        academic_level=academic_level,
        program_id=program_id,
        department_id=department_id,
        research_field=research_field,
        year_published=year_published,
        availability=availability,
        author=author,
        **filter_options
    )


# ============================================================
# AUTOCOMPLETE API
# ============================================================

@bp.route("/api/search-suggestions")
def search_suggestions():

    query = request.args.get(
        "q",
        ""
    ).strip()

    if len(query) < 1:

        return jsonify(
            []
        )

    suggestions = (
        get_autocomplete_suggestions(
            query
        )
    )

    return jsonify(
        suggestions
    )


# ============================================================
# THESIS DETAILS
# ============================================================

@bp.route("/thesis/<int:thesis_id>")
def thesis_details(thesis_id):

    thesis = (
        Thesis.query
        .filter(
            Thesis.id == thesis_id,
            Thesis.is_archived.is_(False)
        )
        .first_or_404()
    )


    related_theses = (
        get_related_theses(
            thesis,
            limit=3
        )
    )


    return render_template(
        "thesis_details.html",
        thesis=thesis,
        related_theses=related_theses
    )


# ============================================================
# BORROWING REQUEST
# ============================================================

@bp.route(
    "/borrow/<int:thesis_id>",
    methods=["GET", "POST"]
)
def borrow_request(thesis_id):

    thesis = (
        Thesis.query
        .filter(
            Thesis.id == thesis_id,
            Thesis.is_archived.is_(False)
        )
        .first_or_404()
    )


    # ========================================================
    # ONLY AVAILABLE THESIS MAY BE REQUESTED
    # ========================================================

    if thesis.availability != "Available":

        return redirect(
            url_for(
                "main.thesis_details",
                thesis_id=thesis.id
            )
        )


    # ========================================================
    # FORM DROPDOWN OPTIONS
    # ========================================================

    academic_levels = (
        AcademicLevel.query
        .order_by(
            AcademicLevel.id
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


    departments = (
        Department.query
        .order_by(
            Department.department_college.asc()
        )
        .all()
    )


    # ========================================================
    # SUBMIT FORM
    # ========================================================

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        gender = request.form.get(
            "gender",
            ""
        )

        age = request.form.get(
            "age",
            type=int
        )

        user_type = request.form.get(
            "user_type",
            ""
        )

        academic_level_id = request.form.get(
            "academic_level_id",
            type=int
        )

        program_id = request.form.get(
            "program_id",
            type=int
        )

        department_id = request.form.get(
            "department_id",
            type=int
        )

        year_level = request.form.get(
            "year_level",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        duration_hours = request.form.get(
            "duration_hours",
            type=float
        )

        borrowing_location = request.form.get(
            "borrowing_location",
            ""
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        errors = []


        if not full_name:

            errors.append(
                "Full name is required."
            )


        if gender not in [
            "Female",
            "Male",
            "Prefer not to say",
        ]:

            errors.append(
                "Please select a valid gender."
            )


        if not age or age < 15 or age > 100:

            errors.append(
                "Please enter a valid age."
            )


        if user_type not in [
            "Student",
            "Faculty",
        ]:

            errors.append(
                "Please select a valid user type."
            )


        if not academic_level_id:

            errors.append(
                "Academic level is required."
            )


        if not program_id:

            errors.append(
                "Course / Program is required."
            )


        if not department_id:

            errors.append(
                "Department / College is required."
            )


        if not address:

            errors.append(
                "Address is required."
            )


        if (
            duration_hours is None
            or duration_hours <= 0
        ):

            errors.append(
                "Borrowing duration is required."
            )


        if borrowing_location not in [
            "Within Library Only",
            "Outside Library / Campus",
        ]:

            errors.append(
                "Please select a valid borrowing location."
            )


        # ====================================================
        # VERIFY DATABASE IDs EXIST
        # ====================================================

        if academic_level_id:

            academic_level_record = db.session.get(
                AcademicLevel,
                academic_level_id
            )

            if not academic_level_record:

                errors.append(
                    "Selected academic level does not exist."
                )


        if program_id:

            program_record = db.session.get(
                Program,
                program_id
            )

            if not program_record:

                errors.append(
                    "Selected program does not exist."
                )


        if department_id:

            department_record = db.session.get(
                Department,
                department_id
            )

            if not department_record:

                errors.append(
                    "Selected department does not exist."
                )


        # ====================================================
        # DISPLAY ERRORS
        # ====================================================

        if errors:

            return render_template(
                "borrow_request.html",
                thesis=thesis,
                academic_levels=academic_levels,
                programs=programs,
                departments=departments,
                errors=errors
            )


        # ====================================================
        # REQUEST / EXPECTED RETURN TIME
        # ====================================================

        requested_borrowing_time = (
            datetime.now()
        )


        expected_return_time = (
            requested_borrowing_time
            +
            timedelta(
                hours=duration_hours
            )
        )


        # ====================================================
        # GENERATE UNIQUE REQUEST NUMBER
        # ====================================================

        next_number = (
            BorrowingRequest.query.count()
            + 1
        )


        request_code = (
            f"BR-{datetime.now().year}-"
            f"{next_number:05d}"
        )


        while (
            BorrowingRequest.query
            .filter_by(
                request_id=request_code
            )
            .first()
        ):

            next_number += 1

            request_code = (
                f"BR-{datetime.now().year}-"
                f"{next_number:05d}"
            )


        # ====================================================
        # CREATE BORROWING REQUEST
        # ====================================================

        borrowing_request = (
            BorrowingRequest(

                request_id=
                    request_code,

                thesis_id=
                    thesis.id,

                full_name=
                    full_name,

                gender=
                    gender,

                age=
                    age,

                user_type=
                    user_type,

                academic_level_id=
                    academic_level_id,

                program_id=
                    program_id,

                department_id=
                    department_id,

                year_level=
                    year_level
                    if year_level
                    else None,

                address=
                    address,

                duration_hours=
                    duration_hours,

                requested_borrowing_time=
                    requested_borrowing_time,

                expected_return_time=
                    expected_return_time,

                borrowing_location=
                    borrowing_location,

                request_date=
                    datetime.now(),

                status=
                    "Requested",
            )
        )


        db.session.add(
            borrowing_request
        )


        db.session.commit()


        # ====================================================
        # IMPORTANT:
        #
        # DO NOT CHANGE THESIS AVAILABILITY HERE.
        #
        # Submitting a request does not mean the thesis
        # has already been borrowed.
        #
        # The Admin will mark it as Borrowed later.
        # ====================================================


        return redirect(
            url_for(
                "main.request_submitted",
                request_id=
                    borrowing_request.id
            )
        )


    # ========================================================
    # GET REQUEST
    # ========================================================

    return render_template(
        "borrow_request.html",
        thesis=thesis,
        academic_levels=academic_levels,
        programs=programs,
        departments=departments,
        errors=[]
    )


# ============================================================
# REQUEST SUBMITTED PAGE
# ============================================================

@bp.route(
    "/request-submitted/<int:request_id>"
)
def request_submitted(request_id):

    borrowing_request = (
        BorrowingRequest.query
        .filter(
            BorrowingRequest.id == request_id
        )
        .first_or_404()
    )


    return render_template(
        "request_submitted.html",
        borrowing_request=
            borrowing_request
    )


# ============================================================
# ABOUT
# ============================================================

@bp.route("/about")
def about():

    return render_template(
        "about.html"
    )