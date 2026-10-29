from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, abort
)
import sqlite3
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "playmaker.db"

app = Flask(
    __name__,
    template_folder="Pages",
    static_folder="Style & JavaScript",
    static_url_path="/assets"
)

app.secret_key = "change-this-key-before-publishing"

SPORTS = [
    "Football",
    "Basketball",
    "Running",
    "Tennis",
    "Volleyball",
    "Cycling",
    "Badminton",
    "Swimming",
    "Gym / Fitness",
    "Table Tennis",
    "Hiking",
    "Other"
]



def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sport TEXT NOT NULL,
                title TEXT NOT NULL,
                activity_date TEXT NOT NULL,
                activity_time TEXT NOT NULL,
                location TEXT NOT NULL,
                max_players INTEGER NOT NULL,
                description TEXT DEFAULT '',
                creator TEXT DEFAULT 'Samyar',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                UNIQUE(activity_id, username),
                FOREIGN KEY(activity_id)
                    REFERENCES activities(id)
                    ON DELETE CASCADE
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS favorite_sports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                sport TEXT NOT NULL,
                UNIQUE(username, sport)
            )
        """)

        count = db.execute(
            "SELECT COUNT(*) FROM activities"
        ).fetchone()[0]

        if count == 0:
            examples = [
                (
                    "Football",
                    "Casual football match",
                    "2026-11-02",
                    "17:30",
                    "Fontys campus field",
                    10,
                    "A relaxed game for anyone who wants to play.",
                    "Alex"
                ),
                (
                    "Running",
                    "Evening running group",
                    "2026-11-03",
                    "18:00",
                    "Stadswandelpark",
                    8,
                    "Easy pace, around 5 km. All levels welcome.",
                    "Jamie"
                ),
                (
                    "Tennis",
                    "Friendly tennis session",
                    "2026-11-05",
                    "16:00",
                    "Tennis Centre Eindhoven",
                    4,
                    "Bring your racket and have fun.",
                    "Robin"
                )
            ]

            db.executemany("""
                INSERT INTO activities (
                    sport, title, activity_date, activity_time,
                    location, max_players, description, creator
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, examples)

        db.execute("""
            DELETE FROM participants
            WHERE EXISTS (
                SELECT 1
                FROM activities
                WHERE activities.id = participants.activity_id
                  AND activities.creator = participants.username
            )
        """)


def current_user():
    return session.get("username", "Samyar")


@app.context_processor
def inject_template_variables():
    username = current_user()
    initials = username.strip()[:2].upper()

    return {
        "current_user": username,
        "user_initials": initials or "U",
        "available_sports": SPORTS
    }


def get_activity(db, activity_id):
    activity = db.execute("""
        SELECT *
        FROM activities
        WHERE id = ?
    """, (activity_id,)).fetchone()

    if activity is None:
        return None

    participants = db.execute("""
        SELECT username
        FROM participants
        WHERE activity_id = ?
        ORDER BY id
    """, (activity_id,)).fetchall()

    data = dict(activity)

    joined_participants = [
        participant["username"]
        for participant in participants
        if participant["username"] != data["creator"]
    ]

    data["participants"] = [
        data["creator"],
        *joined_participants
    ]

    data["joined_count"] = len(data["participants"])

    data["available"] = max(
        0,
        data["max_players"] - data["joined_count"]
    )

    data["joined_by_me"] = (
        current_user() in joined_participants
    )

    return data


def all_activities():
    with connect_db() as db:
        rows = db.execute("""
            SELECT id
            FROM activities
            ORDER BY activity_date, activity_time
        """).fetchall()

        return [
            get_activity(db, row["id"])
            for row in rows
        ]


def get_favorite_sports(username):
    with connect_db() as db:
        rows = db.execute("""
            SELECT sport
            FROM favorite_sports
            WHERE username = ?
            ORDER BY sport
        """, (username,)).fetchall()

    return [row["sport"] for row in rows]



@app.route("/")
def home():
    activities = all_activities()

    activities = [
        activity for activity in activities
        if activity["creator"] != current_user()
    ]

    sport = request.args.get("sport", "").strip()
    search = request.args.get("q", "").strip().lower()

    if sport and sport != "All sports":
        activities = [
            activity for activity in activities
            if activity["sport"] == sport
        ]

    if search:
        activities = [
            activity for activity in activities
            if search in (
                activity["title"] + " "
                + activity["sport"] + " "
                + activity["location"]
            ).lower()
        ]

    return render_template(
        "home.html",
        activities=activities,
        sports=SPORTS,
        selected_sport=sport,
        search=search,
        today=date.today().isoformat()
    )



@app.route("/activities/<int:activity_id>")
def activity_detail(activity_id):
    with connect_db() as db:
        activity = get_activity(db, activity_id)

    if activity is None:
        flash("That activity could not be found.")
        return redirect(url_for("home"))

    return render_template(
        "activity_detail.html",
        activity=activity
    )



@app.route("/activities/create", methods=["GET", "POST"])
def create_activity():
    if request.method == "POST":
        sport = request.form.get("sport", "").strip()
        title = request.form.get("title", "").strip()
        activity_date = request.form.get(
            "activity_date", ""
        ).strip()
        activity_time = request.form.get(
            "activity_time", ""
        ).strip()
        location = request.form.get("location", "").strip()
        max_players = request.form.get(
            "max_players", "6"
        ).strip()
        description = request.form.get(
            "description", ""
        ).strip()

        if not all([
            sport, title, activity_date,
            activity_time, location, max_players
        ]):
            flash("Please complete all required fields.")
            return render_template(
                "create_activity.html",
                form=request.form,
                today=date.today().isoformat()
            )

        if sport not in SPORTS:
            flash("Please select a sport from the list.")
            return render_template(
                "create_activity.html",
                form=request.form,
                today=date.today().isoformat()
            )

        try:
            max_players = int(max_players)

            if not 2 <= max_players <= 100:
                raise ValueError

        except ValueError:
            flash(
                "The number of players must be between 2 and 100."
            )
            return render_template(
                "create_activity.html",
                form=request.form,
                today=date.today().isoformat()
            )

        if activity_date < date.today().isoformat():
            flash("Please select today or a future date.")
            return render_template(
                "create_activity.html",
                form=request.form,
                today=date.today().isoformat()
            )

        with connect_db() as db:
            cursor = db.execute("""
                INSERT INTO activities (
                    sport, title, activity_date, activity_time,
                    location, max_players, description, creator
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sport,
                title,
                activity_date,
                activity_time,
                location,
                max_players,
                description,
                current_user()
            ))

            activity_id = cursor.lastrowid


        flash("Your activity has been created.")

        return redirect(
            url_for(
                "activity_detail",
                activity_id=activity_id
            )
        )

    return render_template(
        "create_activity.html",
        form={},
        today=date.today().isoformat()
    )



@app.route(
    "/activities/<int:activity_id>/join",
    methods=["POST"]
)
def join_activity(activity_id):
    with connect_db() as db:
        activity = get_activity(db, activity_id)

        if activity is None:
            flash("That activity could not be found.")
            return redirect(url_for("home"))

        if activity["creator"] == current_user():
            flash("You created this activity.")

            return redirect(
                url_for(
                    "activity_detail",
                    activity_id=activity_id
                )
            )

        if activity["joined_by_me"]:
            flash("You have already joined this activity.")

            return redirect(
                url_for(
                    "activity_detail",
                    activity_id=activity_id
                )
            )

        if activity["available"] <= 0:
            flash("Sorry, this activity is full.")

            return redirect(
                url_for(
                    "activity_detail",
                    activity_id=activity_id
                )
            )

        db.execute("""
            INSERT OR IGNORE INTO participants
                (activity_id, username)
            VALUES (?, ?)
        """, (activity_id, current_user()))

    return redirect(
        url_for("joined", activity_id=activity_id)
    )



@app.route(
    "/activities/<int:activity_id>/leave",
    methods=["POST"]
)
def leave_activity(activity_id):
    with connect_db() as db:
        activity = db.execute("""
            SELECT creator
            FROM activities
            WHERE id = ?
        """, (activity_id,)).fetchone()

        if activity is None:
            flash("That activity could not be found.")
            return redirect(url_for("my_activities"))

        if activity["creator"] == current_user():
            flash("You cannot leave an activity you created.")

            return redirect(
                url_for("my_activities", tab="created")
            )

        db.execute("""
            DELETE FROM participants
            WHERE activity_id = ?
              AND username = ?
        """, (activity_id, current_user()))

    flash("You left the activity.")
    return redirect(url_for("my_activities"))



@app.route(
    "/activities/<int:activity_id>/delete",
    methods=["POST"]
)
def delete_activity(activity_id):
    with connect_db() as db:
        activity = db.execute("""
            SELECT id, creator
            FROM activities
            WHERE id = ?
        """, (activity_id,)).fetchone()

        if activity is None:
            flash("That activity could not be found.")
            return redirect(url_for("my_activities"))

        if activity["creator"] != current_user():
            abort(403)

        db.execute("""
            DELETE FROM participants
            WHERE activity_id = ?
        """, (activity_id,))

        db.execute("""
            DELETE FROM activities
            WHERE id = ?
        """, (activity_id,))

    flash("Your activity has been deleted.")

    return redirect(
        url_for("my_activities", tab="created")
    )



@app.route("/joined/<int:activity_id>")
def joined(activity_id):
    with connect_db() as db:
        activity = get_activity(db, activity_id)

    if activity is None:
        flash("That activity could not be found.")
        return redirect(url_for("home"))

    return render_template(
        "joined.html",
        activity=activity
    )



@app.route("/my-activities")
def my_activities():
    activities = all_activities()
    username = current_user()

    joined_activities = [
        activity for activity in activities
        if activity["creator"] != username
        and username in activity["participants"]
    ]

    created_activities = [
        activity for activity in activities
        if activity["creator"] == username
    ]

    tab = request.args.get("tab", "joined")

    if tab == "created":
        shown_activities = created_activities
    else:
        tab = "joined"
        shown_activities = joined_activities

    return render_template(
        "my_activities.html",
        activities=shown_activities,
        tab=tab,
        joined_count=len(joined_activities),
        created_count=len(created_activities)
    )



@app.route("/profile")
def profile():
    activities = all_activities()
    username = current_user()

    joined_count = sum(
        activity["creator"] != username
        and username in activity["participants"]
        for activity in activities
    )

    created_count = sum(
        activity["creator"] == username
        for activity in activities
    )

    favorite_sports = get_favorite_sports(username)

    return render_template(
        "profile.html",
        joined_count=joined_count,
        created_count=created_count,
        favorite_sports=favorite_sports
    )



@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    old_username = current_user()

    if request.method == "POST":
        new_username = request.form.get(
            "username", ""
        ).strip()

        selected_sports = request.form.getlist("sports")
        selected_sports = list(dict.fromkeys(
            sport for sport in selected_sports
            if sport in SPORTS
        ))

        if not new_username:
            flash("Please enter a display name.")

            return render_template(
                "edit_profile.html",
                username=old_username,
                favorite_sports=get_favorite_sports(old_username)
            )

        new_username = new_username[:30]

        with connect_db() as db:
            db.execute("""
                UPDATE activities
                SET creator = ?
                WHERE creator = ?
            """, (new_username, old_username))

            old_participations = db.execute("""
                SELECT activity_id
                FROM participants
                WHERE username = ?
            """, (old_username,)).fetchall()

            for participation in old_participations:
                activity_id = participation["activity_id"]

                creator = db.execute("""
                    SELECT creator
                    FROM activities
                    WHERE id = ?
                """, (activity_id,)).fetchone()

                if creator and creator["creator"] == new_username:
                    continue

                db.execute("""
                    INSERT OR IGNORE INTO participants
                        (activity_id, username)
                    VALUES (?, ?)
                """, (activity_id, new_username))

            db.execute("""
                DELETE FROM participants
                WHERE username = ?
            """, (old_username,))

            db.execute("""
                DELETE FROM favorite_sports
                WHERE username = ?
            """, (old_username,))

            db.executemany("""
                INSERT OR IGNORE INTO favorite_sports
                    (username, sport)
                VALUES (?, ?)
            """, [
                (new_username, sport)
                for sport in selected_sports
            ])

            db.execute("""
                DELETE FROM participants
                WHERE username = ?
                  AND activity_id IN (
                      SELECT id
                      FROM activities
                      WHERE creator = ?
                  )
            """, (new_username, new_username))

        session["username"] = new_username
        flash("Your profile has been updated.")

        return redirect(url_for("profile"))

    return render_template(
        "edit_profile.html",
        username=old_username,
        favorite_sports=get_favorite_sports(old_username)
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
