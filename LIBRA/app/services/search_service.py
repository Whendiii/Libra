from sqlalchemy import or_, func

from app import db
from app.models import (
    Thesis,
    Program,
    Department,
    AcademicLevel,
    SearchLog,
)


# ============================================================
# NORMALIZE SEARCH TEXT
# ============================================================

def normalize_query(value):
    """
    Convert search text into a consistent format.

    Example:
        "  Machine   Learning "
    becomes:
        "machine learning"
    """

    if not value:
        return ""

    return " ".join(
        value.lower().strip().split()
    )


# ============================================================
# SEARCH THESIS
# ============================================================

def build_thesis_search(
    query_text="",
    academic_level="",
    program_id="",
    department_id="",
    research_field="",
    year_published="",
    availability="",
    author="",
):
    """
    Build the main LIBRA thesis search query.

    Searchable fields:
    - Thesis title
    - Author / researchers
    - Keywords
    - Research field
    - Research topic
    - Research subtopic
    - Program
    - Department / College

    Filters:
    - Academic level
    - Program
    - Department
    - Research field
    - Year
    - Availability
    - Author
    """

    query = (
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
    # MAIN KEYWORD SEARCH
    # ========================================================

    if query_text:

        pattern = f"%{query_text}%"

        query = query.filter(
            or_(

                Thesis.title.ilike(pattern),

                Thesis.author_researchers.ilike(pattern),

                Thesis.keywords.ilike(pattern),

                Thesis.research_field.ilike(pattern),

                Thesis.research_topic.ilike(pattern),

                Thesis.research_subtopic.ilike(pattern),

                Program.program_name.ilike(pattern),

                Department.department_college.ilike(pattern),

            )
        )


    # ========================================================
    # ACADEMIC LEVEL FILTER
    # ========================================================

    if academic_level:

        query = query.filter(
            AcademicLevel.level_code == academic_level
        )


    # ========================================================
    # PROGRAM FILTER
    # ========================================================

    if program_id:

        try:

            program_id_value = int(
                program_id
            )

            query = query.filter(
                Program.id == program_id_value
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # DEPARTMENT FILTER
    # ========================================================

    if department_id:

        try:

            department_id_value = int(
                department_id
            )

            query = query.filter(
                Department.id == department_id_value
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # RESEARCH FIELD FILTER
    # ========================================================

    if research_field:

        query = query.filter(
            Thesis.research_field == research_field
        )


    # ========================================================
    # YEAR FILTER
    # ========================================================

    if year_published:

        try:

            year_value = int(
                year_published
            )

            query = query.filter(
                Thesis.year_published == year_value
            )

        except (ValueError, TypeError):

            pass


    # ========================================================
    # AVAILABILITY FILTER
    # ========================================================

    if availability:

        query = query.filter(
            Thesis.availability == availability
        )


    # ========================================================
    # AUTHOR FILTER
    # ========================================================

    if author:

        query = query.filter(
            Thesis.author_researchers.ilike(
                f"%{author}%"
            )
        )


    return query


# ============================================================
# AUTOCOMPLETE SUGGESTIONS
# ============================================================

def get_autocomplete_suggestions(
    search_text,
    limit=8
):
    """
    Google-like autocomplete suggestions.

    Suggestions can come from:

    1. Popular/frequently searched terms
    2. Research topics
    3. Research fields
    4. Thesis titles

    Personal recent searches are handled separately
    in search.js using browser localStorage.
    """

    normalized = normalize_query(
        search_text
    )


    if not normalized:

        return []


    suggestions = []

    used_values = set()


    # ========================================================
    # 1. POPULAR / FREQUENT SEARCHES
    # ========================================================

    popular_searches = (
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

            SearchLog.normalized_query != "",

            SearchLog.normalized_query.ilike(
                f"%{normalized}%"
            )

        )

        .group_by(
            SearchLog.normalized_query
        )

        .order_by(
            func.count(
                SearchLog.id
            ).desc()
        )

        .limit(4)

        .all()
    )


    for item in popular_searches:

        value = (
            item.normalized_query or ""
        ).strip()


        if not value:
            continue


        value_key = value.lower()


        if value_key in used_values:
            continue


        suggestions.append(
            {
                "type": "popular",

                "label": value.title(),

                "value": value,

                "count": item.search_count,
            }
        )


        used_values.add(
            value_key
        )


        if len(suggestions) >= limit:

            return suggestions[:limit]


    # ========================================================
    # 2. MATCHING RESEARCH TOPICS
    # ========================================================

    topics = (
        db.session.query(
            Thesis.research_topic
        )

        .filter(

            Thesis.is_archived.is_(False),

            Thesis.research_topic.isnot(None),

            Thesis.research_topic != "",

            Thesis.research_topic.ilike(
                f"%{search_text}%"
            )

        )

        .distinct()

        .order_by(
            Thesis.research_topic.asc()
        )

        .limit(3)

        .all()
    )


    for row in topics:

        value = (
            row[0] or ""
        ).strip()


        if not value:
            continue


        value_key = value.lower()


        if value_key in used_values:
            continue


        suggestions.append(
            {
                "type": "topic",

                "label": value,

                "value": value,
            }
        )


        used_values.add(
            value_key
        )


        if len(suggestions) >= limit:

            return suggestions[:limit]


    # ========================================================
    # 3. MATCHING RESEARCH FIELDS
    # ========================================================

    fields = (
        db.session.query(
            Thesis.research_field
        )

        .filter(

            Thesis.is_archived.is_(False),

            Thesis.research_field.isnot(None),

            Thesis.research_field != "",

            Thesis.research_field.ilike(
                f"%{search_text}%"
            )

        )

        .distinct()

        .order_by(
            Thesis.research_field.asc()
        )

        .limit(2)

        .all()
    )


    for row in fields:

        value = (
            row[0] or ""
        ).strip()


        if not value:
            continue


        value_key = value.lower()


        if value_key in used_values:
            continue


        suggestions.append(
            {
                "type": "field",

                "label": value,

                "value": value,
            }
        )


        used_values.add(
            value_key
        )


        if len(suggestions) >= limit:

            return suggestions[:limit]


    # ========================================================
    # 4. MATCHING THESIS TITLES
    # ========================================================

    remaining = max(
        0,
        limit - len(suggestions)
    )


    if remaining > 0:

        theses = (
            Thesis.query

            .filter(

                Thesis.is_archived.is_(False),

                or_(

                    Thesis.title.ilike(
                        f"%{search_text}%"
                    ),

                    Thesis.keywords.ilike(
                        f"%{search_text}%"
                    ),

                    Thesis.research_topic.ilike(
                        f"%{search_text}%"
                    ),

                    Thesis.research_field.ilike(
                        f"%{search_text}%"
                    ),

                    Thesis.research_subtopic.ilike(
                        f"%{search_text}%"
                    ),

                )

            )

            .order_by(
                Thesis.year_published.desc(),
                Thesis.title.asc()
            )

            .limit(
                remaining
            )

            .all()
        )


        for thesis in theses:

            value = (
                thesis.title or ""
            ).strip()


            if not value:
                continue


            value_key = value.lower()


            if value_key in used_values:
                continue


            # -----------------------------------------------
            # PROGRAM NAME
            # -----------------------------------------------

            program_name = ""

            if thesis.program:

                program_name = (
                    thesis.program.program_name
                    or ""
                )


            suggestions.append(
                {
                    "type": "thesis",

                    "label": thesis.title,

                    "value": thesis.title,

                    "thesis_id": thesis.id,

                    "year": thesis.year_published,

                    "program": program_name,
                }
            )


            used_values.add(
                value_key
            )


            if len(suggestions) >= limit:

                break


    return suggestions[:limit]


# ============================================================
# DATABASE FILTER OPTIONS
# ============================================================

def get_search_filter_options():
    """
    Load filter options directly from the LIBRA database.

    This keeps the Search page dynamic instead of
    hard-coding programs, departments, fields and years.
    """


    # ========================================================
    # ACADEMIC LEVELS
    # ========================================================

    academic_levels = (
        AcademicLevel.query

        .order_by(
            AcademicLevel.id
        )

        .all()
    )


    # ========================================================
    # PROGRAMS
    # ========================================================

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


    # ========================================================
    # DEPARTMENTS / COLLEGES
    # ========================================================

    departments = (
        Department.query

        .order_by(
            Department.department_college.asc()
        )

        .all()
    )


    # ========================================================
    # RESEARCH FIELDS
    # ========================================================

    research_fields = (
        db.session.query(
            Thesis.research_field
        )

        .filter(

            Thesis.research_field.isnot(None),

            Thesis.research_field != "",

            Thesis.is_archived.is_(False)

        )

        .distinct()

        .order_by(
            Thesis.research_field.asc()
        )

        .all()
    )


    # ========================================================
    # YEARS
    # ========================================================

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


    # ========================================================
    # RETURN ALL FILTER OPTIONS
    # ========================================================

    return {

        "academic_levels":
            academic_levels,

        "programs":
            programs,

        "departments":
            departments,

        "research_fields":
            [
                row[0]
                for row in research_fields
                if row[0]
            ],

        "years":
            [
                row[0]
                for row in years
                if row[0] is not None
            ],

    }