import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from werkzeug.security import generate_password_hash


# ============================================================
# PROJECT PATH
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ============================================================
# FLASK / DATABASE IMPORTS
# ============================================================

from app import create_app, db

from app.models import (
    AcademicLevel,
    Department,
    Program,
    Thesis,
    Admin,
    BorrowingRequest,
    Transaction,
    SearchLog,
)


# ============================================================
# EXCEL FILE
# ============================================================

EXCEL_FILE = ROOT_DIR / "LIBRA_Final_Synthetic_Dataset_1000.xlsx"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """
    Convert Excel values safely into clean strings.
    Blank/NaN values become None.
    """

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def clean_int(value, default=None):
    """
    Convert Excel numeric values safely into integers.
    """

    if pd.isna(value):
        return default

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def clean_float(value, default=None):
    """
    Convert Excel numeric values safely into float.
    """

    if pd.isna(value):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clean_datetime(value):
    """
    Convert Excel date/datetime to Python datetime.
    """

    if pd.isna(value):
        return None

    if isinstance(value, datetime):
        return value

    converted = pd.to_datetime(value, errors="coerce")

    if pd.isna(converted):
        return None

    return converted.to_pydatetime()


def combine_date_and_time(date_value, time_value):
    """
    Build one datetime from separate Excel date/time fields.
    """

    if pd.isna(date_value) or pd.isna(time_value):
        return None

    date_obj = pd.to_datetime(date_value, errors="coerce")

    if pd.isna(date_obj):
        return None

    time_text = str(time_value).strip()

    try:
        parsed_time = datetime.strptime(
            time_text,
            "%H:%M:%S"
        ).time()

    except ValueError:

        try:
            parsed_time = datetime.strptime(
                time_text,
                "%H:%M"
            ).time()

        except ValueError:
            return None

    return datetime.combine(
        date_obj.date(),
        parsed_time
    )


# ============================================================
# LOAD EXCEL SHEETS
# ============================================================

def load_sheets():

    print("\nReading synthetic dataset...")

    if not EXCEL_FILE.exists():

        raise FileNotFoundError(
            f"\nExcel file not found:\n{EXCEL_FILE}\n"
        )

    sheets = pd.read_excel(
        EXCEL_FILE,
        sheet_name=None,
        engine="openpyxl"
    )

    required = [
        "Thesis Records",
        "Borrowing Requests",
        "Transactions",
        "Search Logs",
        "Admin Demo",
    ]

    for sheet in required:

        if sheet not in sheets:

            raise ValueError(
                f"Missing Excel sheet: {sheet}"
            )

    print("✅ Excel dataset loaded successfully.")

    return sheets


# ============================================================
# DATABASE REFERENCE MAPS
# ============================================================

def build_reference_maps():

    levels = AcademicLevel.query.all()
    departments = Department.query.all()
    programs = Program.query.all()

    level_map = {
        level.level_code.strip(): level.id
        for level in levels
    }

    department_map = {
        department.department_code.strip(): department.id
        for department in departments
    }

    program_map = {
        program.program_name.strip(): program.id
        for program in programs
    }

    print("\nMaster data detected:")
    print(f"Academic Levels: {len(level_map)}")
    print(f"Departments:     {len(department_map)}")
    print(f"Programs:        {len(program_map)}")

    return (
        level_map,
        department_map,
        program_map
    )


# ============================================================
# 1. SEED THESES
# ============================================================

def seed_theses(df, program_map):

    print("\n========================================")
    print("IMPORTING THESIS RECORDS")
    print("========================================")

    existing_codes = {
        row[0]
        for row in db.session.query(
            Thesis.thesis_code
        ).all()
    }

    inserted = 0
    skipped = 0
    missing_programs = set()

    for _, row in df.iterrows():

        thesis_code = clean_text(
            row.get("thesis_code")
        )

        if not thesis_code:
            skipped += 1
            continue

        if thesis_code in existing_codes:
            skipped += 1
            continue

        program_name = clean_text(
            row.get("program")
        )

        program_id = program_map.get(
            program_name
        )

        if not program_id:

            missing_programs.add(
                program_name
            )

            skipped += 1
            continue

        availability = clean_text(
            row.get("availability")
        ) or "Available"

        if availability not in [
            "Available",
            "Borrowed",
        ]:
            availability = "Available"

        thesis = Thesis(

            thesis_code=thesis_code,

            title=clean_text(
                row.get("title")
            ) or "Untitled Synthetic Research",

            author_researchers=clean_text(
                row.get("author_researchers")
            ) or "Synthetic Researcher",

            program_id=program_id,

            year_published=clean_int(
                row.get("year_published"),
                2026
            ),

            abstract=clean_text(
                row.get("abstract")
            ) or "Synthetic research abstract.",

            keywords=clean_text(
                row.get("keywords")
            ) or "Synthetic Research",

            research_field=clean_text(
                row.get("research_field")
            ) or "General Research",

            research_topic=clean_text(
                row.get("research_topic")
            ) or "General Topic",

            research_subtopic=clean_text(
                row.get("research_subtopic")
            ),

            shelf_location=clean_text(
                row.get("shelf_location")
            ) or "Unassigned",

            availability=availability,

            is_archived=bool(
                row.get("is_archived", False)
            ),
        )

        db.session.add(thesis)

        existing_codes.add(
            thesis_code
        )

        inserted += 1

        # Commit in batches.
        if inserted % 200 == 0:

            db.session.commit()

            print(
                f"  Imported {inserted} thesis records..."
            )

    db.session.commit()

    if missing_programs:

        print("\n⚠️ These Excel programs were not found in MySQL:")

        for program in sorted(missing_programs):
            print(" -", program)

    print(
        f"\n✅ Thesis import finished."
    )

    print(
        f"Inserted: {inserted}"
    )

    print(
        f"Skipped:  {skipped}"
    )


# ============================================================
# BUILD THESIS MAP
# ============================================================

def get_thesis_maps():

    theses = Thesis.query.all()

    code_map = {
        thesis.thesis_code: thesis.id
        for thesis in theses
    }

    return code_map


# ============================================================
# 2. SEED BORROWING REQUESTS
# ============================================================

def seed_borrowing_requests(
    df,
    level_map,
    department_map,
    program_map,
    thesis_code_map
):

    print("\n========================================")
    print("IMPORTING BORROWING REQUESTS")
    print("========================================")

    existing_ids = {
        row[0]
        for row in db.session.query(
            BorrowingRequest.request_id
        ).all()
    }

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():

        request_id = clean_text(
            row.get("request_id")
        )

        if not request_id:
            skipped += 1
            continue

        if request_id in existing_ids:
            skipped += 1
            continue

        thesis_code = clean_text(
            row.get("thesis_code")
        )

        thesis_id = thesis_code_map.get(
            thesis_code
        )

        if not thesis_id:

            print(
                f"⚠️ Missing thesis for request "
                f"{request_id}: {thesis_code}"
            )

            skipped += 1
            continue

        academic_code = clean_text(
            row.get("academic_level")
        )

        program_name = clean_text(
            row.get("program")
        )

        department_code = clean_text(
            row.get("department_code")
        )

        status = clean_text(
            row.get("status")
        ) or "Requested"

        if status not in [
            "Requested",
            "Borrowed",
            "Returned",
        ]:
            status = "Requested"

        gender = clean_text(
            row.get("gender")
        ) or "Prefer not to say"

        if gender not in [
            "Female",
            "Male",
            "Prefer not to say",
        ]:
            gender = "Prefer not to say"

        user_type = clean_text(
            row.get("user_type")
        ) or "Student"

        if user_type not in [
            "Student",
            "Faculty",
        ]:
            user_type = "Student"

        borrowing_location = clean_text(
            row.get("borrowing_location")
        ) or "Within Library Only"

        if borrowing_location not in [
            "Within Library Only",
            "Outside Library / Campus",
        ]:
            borrowing_location = "Within Library Only"

        request = BorrowingRequest(

            request_id=request_id,

            thesis_id=thesis_id,

            full_name=clean_text(
                row.get("full_name")
            ) or "Synthetic Borrower",

            gender=gender,

            age=clean_int(
                row.get("age"),
                18
            ),

            user_type=user_type,

            academic_level_id=level_map.get(
                academic_code
            ),

            program_id=program_map.get(
                program_name
            ),

            department_id=department_map.get(
                department_code
            ),

            year_level=clean_text(
                row.get("year_level")
            ),

            address=clean_text(
                row.get("address")
            ) or "Synthetic Address",

            duration_hours=clean_float(
                row.get("duration_hours"),
                1
            ),

            requested_borrowing_time=clean_datetime(
                row.get(
                    "requested_borrowing_time"
                )
            ),

            expected_return_time=clean_datetime(
                row.get(
                    "expected_return_time"
                )
            ),

            borrowing_location=borrowing_location,

            request_date=clean_datetime(
                row.get("request_date")
            ) or datetime.utcnow(),

            status=status,
        )

        if not request.requested_borrowing_time:
            skipped += 1
            continue

        if not request.expected_return_time:
            skipped += 1
            continue

        db.session.add(request)

        existing_ids.add(
            request_id
        )

        inserted += 1

        if inserted % 100 == 0:

            db.session.commit()

            print(
                f"  Imported {inserted} requests..."
            )

    db.session.commit()

    print(
        f"\n✅ Borrowing request import finished."
    )

    print(
        f"Inserted: {inserted}"
    )

    print(
        f"Skipped:  {skipped}"
    )


# ============================================================
# BORROWING REQUEST MAP
# ============================================================

def get_request_map():

    requests = BorrowingRequest.query.all()

    return {
        request.request_id: request.id
        for request in requests
    }


# ============================================================
# 3. SEED TRANSACTIONS
# ============================================================

def seed_transactions(
    df,
    request_map,
    thesis_code_map
):

    print("\n========================================")
    print("IMPORTING TRANSACTIONS")
    print("========================================")

    existing_ids = {
        row[0]
        for row in db.session.query(
            Transaction.transaction_id
        ).all()
    }

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():

        transaction_id = clean_text(
            row.get("transaction_id")
        )

        if not transaction_id:
            skipped += 1
            continue

        if transaction_id in existing_ids:
            skipped += 1
            continue

        request_id = clean_text(
            row.get("request_id")
        )

        request_db_id = request_map.get(
            request_id
        )

        thesis_code = clean_text(
            row.get("thesis_code")
        )

        thesis_id = thesis_code_map.get(
            thesis_code
        )

        if not request_db_id or not thesis_id:
            skipped += 1
            continue

        date_borrowed = row.get(
            "date_borrowed"
        )

        time_borrowed = row.get(
            "time_borrowed"
        )

        date_time_borrowed = combine_date_and_time(
            date_borrowed,
            time_borrowed
        )

        expected_time = row.get(
            "expected_return_time"
        )

        expected_return = combine_date_and_time(
            date_borrowed,
            expected_time
        )

        # If expected time falls after midnight,
        # move to next day.
        if (
            expected_return
            and date_time_borrowed
            and expected_return < date_time_borrowed
        ):
            expected_return += timedelta(days=1)

        actual_return = None

        if clean_text(
            row.get("actual_return_date")
        ):

            actual_return = combine_date_and_time(
                row.get("actual_return_date"),
                row.get("actual_return_time")
            )

        status = clean_text(
            row.get("status")
        ) or "Borrowed"

        if status not in [
            "Borrowed",
            "Returned",
        ]:
            status = "Borrowed"

        borrowing_location = clean_text(
            row.get("borrowing_location")
        ) or "Within Library Only"

        if borrowing_location not in [
            "Within Library Only",
            "Outside Library / Campus",
        ]:
            borrowing_location = "Within Library Only"

        if not date_time_borrowed:
            skipped += 1
            continue

        if not expected_return:
            skipped += 1
            continue

        transaction = Transaction(

            transaction_id=transaction_id,

            borrowing_request_id=request_db_id,

            thesis_id=thesis_id,

            date_time_borrowed=date_time_borrowed,

            expected_return_time=expected_return,

            borrowing_location=borrowing_location,

            actual_return_time=actual_return,

            status=status,
        )

        db.session.add(transaction)

        existing_ids.add(
            transaction_id
        )

        inserted += 1

        if inserted % 100 == 0:

            db.session.commit()

            print(
                f"  Imported {inserted} transactions..."
            )

    db.session.commit()

    print(
        f"\n✅ Transaction import finished."
    )

    print(
        f"Inserted: {inserted}"
    )

    print(
        f"Skipped:  {skipped}"
    )


# ============================================================
# 4. SEED SEARCH LOGS
# ============================================================

def seed_search_logs(
    df,
    level_map,
    program_map,
    thesis_code_map
):

    print("\n========================================")
    print("IMPORTING SEARCH LOGS")
    print("========================================")

    existing_ids = {
        row[0]
        for row in db.session.query(
            SearchLog.search_id
        ).all()
    }

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():

        search_id = clean_text(
            row.get("search_id")
        )

        if not search_id:
            skipped += 1
            continue

        if search_id in existing_ids:
            skipped += 1
            continue

        level_code = clean_text(
            row.get("academic_level_filter")
        )

        program_name = clean_text(
            row.get("program_filter")
        )

        clicked_code = clean_text(
            row.get("clicked_thesis_code")
        )

        clicked_thesis_id = (
            thesis_code_map.get(clicked_code)
            if clicked_code
            else None
        )

        log = SearchLog(

            search_id=search_id,

            searched_at=clean_datetime(
                row.get("searched_at")
            ) or datetime.utcnow(),

            search_query=clean_text(
                row.get("query")
            ) or "",

            normalized_query=clean_text(
                row.get("normalized_query")
            ) or "",

            topic_bucket=clean_text(
                row.get("topic_bucket")
            ),

            academic_level_id=level_map.get(
                level_code
            ),

            program_id=program_map.get(
                program_name
            ),

            research_field_filter=clean_text(
                row.get("research_field_filter")
            ),

            result_count=clean_int(
                row.get("result_count"),
                0
            ),

            clicked_thesis_id=clicked_thesis_id,
        )

        db.session.add(log)

        existing_ids.add(
            search_id
        )

        inserted += 1

        if inserted % 1000 == 0:

            db.session.commit()

            print(
                f"  Imported {inserted} search logs..."
            )

    db.session.commit()

    print(
        f"\n✅ Search log import finished."
    )

    print(
        f"Inserted: {inserted}"
    )

    print(
        f"Skipped:  {skipped}"
    )


# ============================================================
# 5. SEED ADMIN
# ============================================================

def seed_admin(df):

    print("\n========================================")
    print("IMPORTING ADMIN DEMO")
    print("========================================")

    inserted = 0

    for _, row in df.iterrows():

        username = clean_text(
            row.get("username")
        )

        password = clean_text(
            row.get("demo_password")
        )

        if not username or not password:
            continue

        existing = Admin.query.filter_by(
            username=username
        ).first()

        if existing:
            print(
                f"Admin '{username}' already exists. Skipping."
            )
            continue

        role = clean_text(
            row.get("role")
        ) or "Administrator"

        if role not in [
            "Administrator",
            "Librarian",
        ]:
            role = "Administrator"

        admin = Admin(

            username=username,

            password_hash=generate_password_hash(
                password
            ),

            display_name=clean_text(
                row.get("display_name")
            ) or "LIBRA Administrator",

            role=role,

            is_active=True,
        )

        db.session.add(admin)

        inserted += 1

    db.session.commit()

    print(
        f"✅ Admin accounts inserted: {inserted}"
    )


# ============================================================
# FINAL DATABASE COUNTS
# ============================================================

def show_final_counts():

    print("\n========================================")
    print("FINAL DATABASE COUNTS")
    print("========================================")

    print(
        "Academic Levels:",
        AcademicLevel.query.count()
    )

    print(
        "Departments:",
        Department.query.count()
    )

    print(
        "Programs:",
        Program.query.count()
    )

    print(
        "Theses:",
        Thesis.query.count()
    )

    print(
        "Borrowing Requests:",
        BorrowingRequest.query.count()
    )

    print(
        "Transactions:",
        Transaction.query.count()
    )

    print(
        "Search Logs:",
        SearchLog.query.count()
    )

    print(
        "Admins:",
        Admin.query.count()
    )


# ============================================================
# MAIN SEED PROCESS
# ============================================================

def main():

    print("\n")
    print("========================================")
    print(" LIBRA SYNTHETIC DATABASE SEEDER")
    print("========================================")

    app = create_app()

    with app.app_context():

        try:

            sheets = load_sheets()

            (
                level_map,
                department_map,
                program_map
            ) = build_reference_maps()

            # --------------------------------------------
            # THESIS
            # --------------------------------------------

            seed_theses(
                sheets["Thesis Records"],
                program_map
            )

            thesis_code_map = get_thesis_maps()

            # --------------------------------------------
            # BORROWING REQUESTS
            # --------------------------------------------

            seed_borrowing_requests(
                sheets["Borrowing Requests"],
                level_map,
                department_map,
                program_map,
                thesis_code_map
            )

            request_map = get_request_map()

            # --------------------------------------------
            # TRANSACTIONS
            # --------------------------------------------

            seed_transactions(
                sheets["Transactions"],
                request_map,
                thesis_code_map
            )

            # --------------------------------------------
            # SEARCH LOGS
            # --------------------------------------------

            seed_search_logs(
                sheets["Search Logs"],
                level_map,
                program_map,
                thesis_code_map
            )

            # --------------------------------------------
            # ADMIN
            # --------------------------------------------

            seed_admin(
                sheets["Admin Demo"]
            )

            # --------------------------------------------
            # FINAL COUNTS
            # --------------------------------------------

            show_final_counts()

            print("\n========================================")
            print("✅ LIBRA DATABASE SEEDING COMPLETE")
            print("========================================\n")

        except Exception as error:

            db.session.rollback()

            print("\n❌ SEEDING ERROR:")
            print(error)

            raise


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()