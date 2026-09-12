from flask import Flask, render_template, request, session, redirect
import sqlite3

app = Flask(__name__)

# Secret key for sessions
app.secret_key = "student-complaint-secret-key"

# Session ends when the browser session ends
app.config["SESSION_PERMANENT"] = False


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_database_connection():

    connection = sqlite3.connect("database.db")

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# STUDENT REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        connection = get_database_connection()

        try:

            connection.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, password)
            )

            connection.commit()

        except sqlite3.IntegrityError:

            connection.close()

            return "Email already registered!"

        connection.close()

        return "Registration successful!"

    return render_template("register.html")


# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_database_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ? AND password = ?
            """,
            (email, password)
        ).fetchone()

        connection.close()

        if user:

            # Clear any old session
            session.clear()

            # Store logged-in student
            session["user_id"] = user["id"]

            return redirect("/dashboard")

        else:

            error = "Invalid email or password! Please try again."

    return render_template(
        "login.html",
        error=error
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # Check student login
    if "user_id" not in session:

        return redirect("/login")

    connection = get_database_connection()

    # Get logged-in student
    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    # Total complaints
    total_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    # Pending complaints
    pending_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE user_id = ?
        AND status = 'Pending'
        """,
        (session["user_id"],)
    ).fetchone()[0]

    # Resolved complaints
    resolved_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE user_id = ?
        AND status = 'Resolved'
        """,
        (session["user_id"],)
    ).fetchone()[0]

    connection.close()

    return render_template(
        "dashboard.html",
        user=user,
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        resolved_complaints=resolved_complaints
    )


# =========================================================
# STUDENT LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# SUBMIT COMPLAINT
# =========================================================

@app.route("/submit-complaint", methods=["GET", "POST"])
def submit_complaint():

    # Student must be logged in
    if "user_id" not in session:

        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        priority = request.form["priority"]
        description = request.form["description"]

        connection = get_database_connection()

        # New complaints start as Pending
        connection.execute(
            """
            INSERT INTO complaints
            (
                user_id,
                title,
                category,
                priority,
                description,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                category,
                priority,
                description,
                "Pending"
            )
        )

        connection.commit()

        connection.close()

        return redirect("/dashboard")

    return render_template("submit_complaint.html")


# =========================================================
# MY COMPLAINTS
# =========================================================

# =========================================================
# STUDENT - MY COMPLAINTS
# SEARCH AND FILTER
# =========================================================

@app.route("/my-complaints")
def my_complaints():

    # Student must be logged in
    if "user_id" not in session:
        return redirect("/login")

    # Get filter values
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()

    connection = get_database_connection()

    # Base query
    query = """
        SELECT *
        FROM complaints
        WHERE user_id = ?
    """

    parameters = [session["user_id"]]

    # Search complaint title or description
    if search:

        query += """
            AND (
                title LIKE ?
                OR description LIKE ?
            )
        """

        search_value = f"%{search}%"

        parameters.extend([
            search_value,
            search_value
        ])

    # Filter by status
    if status:

        query += """
            AND status = ?
        """

        parameters.append(status)

    # Filter by priority
    if priority:

        query += """
            AND priority = ?
        """

        parameters.append(priority)

    # Latest complaints first
    query += """
        ORDER BY id DESC
    """

    complaints = connection.execute(
        query,
        parameters
    ).fetchall()

    connection.close()

    return render_template(
        "my_complaints.html",
        complaints=complaints,
        search=search,
        status=status,
        priority=priority
    )
# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        # Admin credentials
        if email == "admin@gmail.com" and password == "admin123":

            # Clear previous session
            session.clear()

            # Create admin session
            session["admin"] = True

            return redirect("/admin-dashboard")

        else:

            error = "Invalid admin email or password!"

    return render_template(
        "admin_login.html",
        error=error
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    # Check admin login
    if not session.get("admin"):

        return redirect("/admin-login")

    connection = get_database_connection()

    # -----------------------------------------
    # Total complaints
    # -----------------------------------------

    total_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        """
    ).fetchone()[0]

    # -----------------------------------------
    # Pending complaints
    # -----------------------------------------

    pending_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE status = 'Pending'
        """
    ).fetchone()[0]

    # -----------------------------------------
    # In Progress complaints
    # -----------------------------------------

    in_progress_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE status = 'In Progress'
        """
    ).fetchone()[0]

    # -----------------------------------------
    # Resolved complaints
    # -----------------------------------------

    resolved_complaints = connection.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE status = 'Resolved'
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "admin_dashboard.html",

        total_complaints=total_complaints,

        pending_complaints=pending_complaints,

        in_progress_complaints=in_progress_complaints,

        resolved_complaints=resolved_complaints
    )


# =========================================================
# ADMIN - VIEW ALL COMPLAINTS
# =========================================================

# =========================================================
# ADMIN - VIEW, SEARCH AND FILTER COMPLAINTS
# =========================================================

@app.route("/admin-complaints")
def admin_complaints():

    # Check admin login
    if not session.get("admin"):
        return redirect("/admin-login")

    # Get filter values from URL
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    category = request.args.get("category", "").strip()

    connection = get_database_connection()

    # Get available categories from database
    categories = connection.execute(
        """
        SELECT DISTINCT category
        FROM complaints
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
        """
    ).fetchall()

    # Base query
    query = """
        SELECT
            complaints.*,
            users.name,
            users.email
        FROM complaints
        JOIN users
        ON complaints.user_id = users.id
    """

    conditions = []
    parameters = []

    # Search by title, student name or email
    if search:

        conditions.append(
            """
            (
                complaints.title LIKE ?
                OR users.name LIKE ?
                OR users.email LIKE ?
            )
            """
        )

        search_value = f"%{search}%"

        parameters.extend([
            search_value,
            search_value,
            search_value
        ])

    # Filter by status
    if status:

        conditions.append(
            "complaints.status = ?"
        )

        parameters.append(status)

    # Filter by priority
    if priority:

        conditions.append(
            "complaints.priority = ?"
        )

        parameters.append(priority)

    # Filter by category
    if category:

        conditions.append(
            "complaints.category = ?"
        )

        parameters.append(category)

    # Add WHERE conditions
    if conditions:

        query += " WHERE " + " AND ".join(conditions)

    # Latest complaints first
    query += " ORDER BY complaints.id DESC"

    # Execute query
    complaints = connection.execute(
        query,
        parameters
    ).fetchall()

    connection.close()

    return render_template(
        "admin_complaints.html",
        complaints=complaints,
        categories=categories,
        search=search,
        status=status,
        priority=priority,
        category=category
    )

# =========================================================
# ADMIN - UPDATE COMPLAINT STATUS
# =========================================================

@app.route(
    "/update-status/<int:complaint_id>",
    methods=["POST"]
)
def update_status(complaint_id):

    # Check admin login
    if not session.get("admin"):

        return redirect("/admin-login")

    status = request.form["status"]

    # Only allow these three statuses
    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:

        return redirect("/admin-complaints")

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE complaints

        SET status = ?

        WHERE id = ?
        """,
        (
            status,
            complaint_id
        )
    )

    connection.commit()

    connection.close()

    return redirect("/admin-complaints")


# =========================================================
# ADMIN - STUDENT MANAGEMENT
# =========================================================

@app.route("/admin-students")
def admin_students():

    # Check admin login
    if not session.get("admin"):
        return redirect("/admin-login")

    # Get search value
    search = request.args.get("search", "").strip()

    connection = get_database_connection()

    # Base query
    query = """
        SELECT
            users.id,
            users.name,
            users.email,
            COUNT(complaints.id) AS complaint_count
        FROM users
        LEFT JOIN complaints
        ON users.id = complaints.user_id
    """

    parameters = []

    # Search students
    if search:

        query += """
            WHERE
                users.name LIKE ?
                OR users.email LIKE ?
        """

        search_value = f"%{search}%"

        parameters.extend([
            search_value,
            search_value
        ])

    # Group students
    query += """
        GROUP BY
            users.id,
            users.name,
            users.email

        ORDER BY
            users.id ASC
    """

    students = connection.execute(
        query,
        parameters
    ).fetchall()

    connection.close()

    return render_template(
        "admin_students.html",
        students=students,
        search=search
    )

# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin-logout")
def admin_logout():

    session.clear()

    return redirect("/admin-login")


# =========================================================
# PREVENT BROWSER CACHING OF PROTECTED PAGES
# =========================================================

@app.after_request
def add_no_cache(response):

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    response.headers["Pragma"] = "no-cache"

    response.headers["Expires"] = "0"

    return response


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)