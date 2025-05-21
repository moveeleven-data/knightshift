from flask import Flask, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from sqlalchemy import func

# Flask app configuration
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@db:5432/knightshift",  # pragma: allowlist secret
)
app.secret_key = os.urandom(24)  # Set a random secret key to handle sessions securely
db = SQLAlchemy(app)
logging.basicConfig(level=logging.DEBUG)

# === ECO DESCRIPTIONS DICTIONARY ===
eco_descriptions = {
    "A0": "Sidelines: Bird's Opening, Reti, King's Indian Attack",
    "A1": "English Opening",
    "A2": "King's English",
    "A3": "English, Symmetrical",
    "A4": "Queen's Pawn Game",
    "A5": "Indian Defence",
    "A6": "Modern Benoni",
    "A7": "Benoni Defence, Modern",
    "A8": "Dutch Defence",
    "A9": "Dutch Defence, Classical",
    "B0": "Alekhine Defence, Modern/Pirc",
    "B1": "Caro-Kann Defence",
    "B2": "Sicilian Defence",
    "B3": "Sicilian, Najdorf Variation",
    "B4": "Sicilian, Dragon Variation",
    "B5": "Sicilian, Scheveningen Variation",
    "B6": "Sicilian, Classical Variation",
    "B7": "Sicilian, Dragon, Accelerated",
    "B8": "Sicilian, Closed System",
    "B9": "Sicilian, Najdorf, English Attack",
    "C0": "French Defence",
    "C1": "French Defence, Winawer Variation",
    "C2": "Open Game, 1.e4 e5",
    "C3": "King's Gambit",
    "C4": "1.e4 e5, King's Knight Opening",
    "C5": "Italian Game",
    "C6": "Ruy Lopez, Spanish Variation",
    "C7": "Ruy Lopez, Closed Variation",
    "C8": "Ruy Lopez, Exchange Variation",
    "C9": "Ruy Lopez, Berlin Defence",
    "D0": "Queen's Pawn Game",
    "D1": "Slav Defence",
    "D2": "Queen's Gambit Accepted",
    "D3": "Queen's Gambit Declined",
    "D4": "Semi-Tarrasch; Semi-Slav",
    "D5": "Queen's Gambit Declined, Classical",
    "D6": "Queen's Gambit Declined, Orthodox Variation",
    "D7": "Grunfeld Defence",
    "D8": "Grunfeld Defence, Russian System",
    "D9": "Grunfeld Defence, Main Line",
    "E0": "Catalan Opening",
    "E1": "Queen's Indian Defence",
    "E2": "Nimzo-Indian Defence",
    "E3": "Nimzo-Indian, Rubinstein Variation",
    "E4": "Nimzo-Indian, Classical Variation",
    "E5": "Nimzo-Indian, Main Line",
    "E6": "King's Indian Defence",
    "E7": "King's Indian Defence, Classical",
    "E8": "King's Indian Defence, Samisch Variation",
    "E9": "King's Indian Defence, Main Lines",
}


# Define your models here...
class Game(db.Model):
    __tablename__ = "tv_channel_games"
    id_game = db.Column(db.String, primary_key=True)
    val_event_name = db.Column(db.String)
    id_user_white = db.Column(db.String)
    id_user_black = db.Column(db.String)
    val_result = db.Column(db.String)
    val_opening_name = db.Column(db.String)
    val_opening_eco_code = db.Column(db.String)
    val_site_url = db.Column(db.String)  # This column stores the URL to the game


class Player(db.Model):
    __tablename__ = "lichess_users"
    id_user = db.Column(db.String, primary_key=True)
    val_username = db.Column(db.String)
    val_rating_classical = db.Column(db.Integer)
    val_rating_rapid = db.Column(db.Integer)
    val_rating_blitz = db.Column(db.Integer)
    val_rating_bullet = db.Column(db.Integer)
    n_games_all = db.Column(db.Integer)
    n_games_win = db.Column(db.Integer)
    n_games_loss = db.Column(db.Integer)
    n_games_draw = db.Column(db.Integer)
    val_url = db.Column(db.Text)  # URL for the Lichess profile
    val_title = db.Column(db.String(10), nullable=True)


@app.route("/", methods=["GET"])
def home():
    app.logger.debug("Rendering home page")
    return render_template("home.html")


@app.route("/games", methods=["GET"])
def get_games():
    app.logger.debug("Fetching all games from database")
    games = Game.query.all()  # Fetch all games, including the game URLs
    return render_template("games.html", games=games)


@app.route("/players", methods=["GET"])
def get_all_players():
    players = Player.query.order_by(Player.val_username.asc()).all()
    return render_template("players.html", players=players)


@app.route("/metrics", methods=["GET"])
def metrics():
    session.clear()  # Clear session data to ensure no stale information is present
    db.session.expire_all()  # Force fresh data to avoid using stale queries
    db.session.remove()  # Remove current session to force a new session

    # Step 1: Get total games and valid players
    total_games = Game.query.count()
    total_players = Player.query.filter(
        Player.val_username.notlike("%anonymous%"),
        Player.n_games_all <= 300000,  # Exclude players with more than 300,000 games
    ).count()

    app.logger.debug(
        f"Total Players (after filtering anonymous and large game count): {total_players}"
    )

    # Step 2: Get the true most active player (the one with the highest number of games)
    top_player = (
        db.session.query(Player.val_username, Player.n_games_all, Player.val_url)
        .filter(
            Player.val_username.notlike("%anonymous%"), Player.n_games_all <= 300000
        )
        .order_by(Player.n_games_all.desc())
        .first()  # Get the player with the most games
    )

    # Debugging the top player fetched
    app.logger.debug(f"Top Player Query Result: {top_player}")

    # Check if the top player is valid and log it
    top_player_name = top_player[0] if top_player else "N/A"
    top_player_url = top_player[2] if top_player else "#"

    app.logger.debug(f"Final Top Player: {top_player_name}, URL: {top_player_url}")

    # Step 3: Get the top 3 most played ECO codes (distinct)
    most_played_eco = (
        db.session.query(
            Game.val_opening_eco_code,
            func.count(Game.val_opening_eco_code).label("count"),
        )
        .filter(
            Game.val_opening_eco_code.isnot(None),
            Game.val_opening_eco_code != "?",
            Game.val_result.isnot(None),
        )
        .group_by(Game.val_opening_eco_code)
        .order_by(func.count(Game.val_opening_eco_code).desc())
        .limit(10)  # Increase the limit to make sure we get enough data to filter later
        .all()
    )

    # Using a set to store unique openings
    unique_openings = set()
    most_played_openings = []

    # Loop through the results to add unique descriptions
    for eco, _ in most_played_eco:
        eco_description = eco_descriptions.get(eco[:2], "Unknown Opening")
        if eco_description not in unique_openings:
            unique_openings.add(eco_description)
            most_played_openings.append(eco_description)

        # Stop once we have 3 unique openings
        if len(most_played_openings) >= 3:
            break

    # If fewer than three unique openings, pad with "Unknown Opening"
    while len(most_played_openings) < 3:
        most_played_openings.append("Unknown Opening")

    app.logger.debug(f"Most Played Openings: {most_played_openings}")

    # Return the response with the correct top player and openings
    return render_template(
        "metrics.html",
        total_games=total_games,
        total_players=total_players,
        top_player=top_player_name,
        top_player_url=top_player_url,
        most_played_openings=most_played_openings,
    )


@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    try:
        # Total games and players
        total_games = Game.query.count()
        total_players = Player.query.filter(
            Player.val_username.notlike("%anonymous%")
        ).count()  # Exclude anonymous players

        # Fetch the top player (player with the most games played excluding 'anonymous' players)
        top_player = (
            db.session.query(
                Player.val_username,
                Player.n_games_all,
                Player.val_title,
                Player.val_url,
            )
            .filter(
                Player.val_username.notlike("%Anonymous%")
            )  # Exclude 'anonymous' players
            .order_by(Player.n_games_all.desc())
            .first()
        )

        # If the top player is anonymous, skip to the next valid player
        if top_player and "Anonymous" in top_player[0].lower():
            top_player = (
                db.session.query(
                    Player.val_username,
                    Player.n_games_all,
                    Player.val_title,
                    Player.val_url,
                )
                .filter(Player.val_username.notlike("%Anonymous%"))
                .order_by(Player.n_games_all.desc())
                .offset(1)  # Skip the first (anonymous) player
                .first()
            )

        # Extract player details
        top_player_name = top_player[0] if top_player else "N/A"
        top_player_games = top_player[1] if top_player else 0
        top_player_title = top_player[2] if top_player and top_player[2] else "None"
        top_player_url = top_player[3] if top_player else "#"

        # Find the top three most played ECO codes (ensure to exclude null or invalid values)
        most_played_eco = (
            db.session.query(
                Game.val_opening_eco_code,
                func.count(Game.val_opening_eco_code).label("count"),
            )
            .filter(
                Game.val_opening_eco_code.isnot(None),
                Game.val_opening_eco_code != "?",
            )
            .group_by(Game.val_opening_eco_code)
            .order_by(func.count(Game.val_opening_eco_code).desc())
            .limit(10)  # Increase the limit to get enough data for filtering later
            .all()
        )

        # Use a set to ensure distinct, valid openings
        unique_openings = set()
        most_played_openings = []

        # Loop through the results and filter for unique ECO codes
        for eco, _ in most_played_eco:
            eco_description = eco_descriptions.get(eco[:2], "Unknown Opening")
            if eco_description not in unique_openings:
                unique_openings.add(eco_description)
                most_played_openings.append(eco_description)

            # Stop once we have 3 unique openings
            if len(most_played_openings) >= 3:
                break

        # If fewer than three openings are found, pad with "Unknown Opening"
        while len(most_played_openings) < 3:
            most_played_openings.append("Unknown Opening")

        return jsonify(
            {
                "total_games": total_games,
                "total_players": total_players,
                "top_player": top_player_name,
                "top_player_url": top_player_url,  # Return the profile URL
                "top_player_games": top_player_games,
                "top_player_title": top_player_title,
                "most_played_openings": most_played_openings,
            }
        )
    except Exception as e:
        app.logger.error(f"Error in /api/metrics: {e}")
        return jsonify({"error": "Failed to fetch metrics"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
