from flask import Flask, jsonify, render_template, session, Response
from flask_sqlalchemy import SQLAlchemy
import os
import logging
import csv
from io import StringIO
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
    val_title = db.Column(db.String(10), nullable=True)
    val_real_name = db.Column(db.String, nullable=True)
    val_location = db.Column(db.String, nullable=True)
    val_bio = db.Column(db.Text, nullable=True)
    val_url = db.Column(db.String, nullable=True)
    val_rating_fide = db.Column(db.Integer, nullable=True)
    val_rating_uscf = db.Column(db.Integer, nullable=True)
    val_rating_bullet = db.Column(db.Integer, nullable=True)
    val_rating_blitz = db.Column(db.Integer, nullable=True)
    val_rating_classical = db.Column(db.Integer, nullable=True)
    val_rating_rapid = db.Column(db.Integer, nullable=True)
    val_rating_chess960 = db.Column(db.Integer, nullable=True)
    val_rating_ultra_bullet = db.Column(db.Integer, nullable=True)
    val_country_code = db.Column(db.String(20), nullable=True)
    tm_created = db.Column(db.BigInteger)
    tm_seen = db.Column(db.BigInteger)
    n_playtime_total = db.Column(db.Integer, nullable=True)
    n_playtime_tv = db.Column(db.Integer, nullable=True)
    n_games_all = db.Column(db.Integer, nullable=True)
    n_games_rated = db.Column(db.Integer, nullable=True)
    n_games_win = db.Column(db.Integer, nullable=True)
    n_games_loss = db.Column(db.Integer, nullable=True)
    n_games_draw = db.Column(db.Integer, nullable=True)
    ind_patron = db.Column(db.Boolean, nullable=True)
    ind_streaming = db.Column(db.Boolean, nullable=True)


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

    # Ensure each player has a valid URL
    for player in players:
        if not player.val_url:
            player.val_url = f"https://lichess.org/@/{player.val_username}"

    return render_template("players.html", players=players)


@app.route("/export_csv", methods=["GET"])
def export_csv():
    # Query all players from the database
    players = Player.query.all()

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(
        [
            "Username",
            "Title",
            "Real Name",
            "Location",
            "Bio",
            "FIDE Rating",
            "USCF Rating",
            "Bullet Rating",
            "Blitz Rating",
            "Classical Rating",
            "Rapid Rating",
            "Chess960 Rating",
            "Ultra Bullet Rating",
            "Country",
            "Profile URL",
            "Total Games",
            "Games Won",
            "Games Lost",
            "Games Drawn",
            "Patron",
            "Streaming",
        ]
    )

    # Write data rows
    for player in players:
        writer.writerow(
            [
                player.val_username,
                player.val_title if player.val_title else "N/A",
                player.val_real_name if player.val_real_name else "N/A",
                player.val_location if player.val_location else "N/A",
                player.val_bio if player.val_bio else "N/A",
                player.val_rating_fide if player.val_rating_fide else "N/A",
                player.val_rating_uscf if player.val_rating_uscf else "N/A",
                player.val_rating_bullet if player.val_rating_bullet else "N/A",
                player.val_rating_blitz if player.val_rating_blitz else "N/A",
                player.val_rating_classical if player.val_rating_classical else "N/A",
                player.val_rating_rapid if player.val_rating_rapid else "N/A",
                player.val_rating_chess960 if player.val_rating_chess960 else "N/A",
                (
                    player.val_rating_ultra_bullet
                    if player.val_rating_ultra_bullet
                    else "N/A"
                ),
                player.val_country_code if player.val_country_code else "N/A",
                player.val_url if player.val_url else "N/A",
                player.n_games_all if player.n_games_all else "N/A",
                player.n_games_win if player.n_games_win else "N/A",
                player.n_games_loss if player.n_games_loss else "N/A",
                player.n_games_draw if player.n_games_draw else "N/A",
                player.ind_patron if player.ind_patron else "N/A",
                player.ind_streaming if player.ind_streaming else "N/A",
            ]
        )

    # Return the CSV file as a response with a download header
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=lichess_users.csv"},
    )


@app.route("/export_all_csv", methods=["GET"])
def export_all_csv():
    # Query all games from the tv_channel_games table
    games = Game.query.all()

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(
        [
            "Game ID",
            "Event Name",
            "White Player ID",
            "Black Player ID",
            "Result",
            "Opening Name",
            "Opening ECO Code",
            "Game URL",
        ]
    )

    # Write data rows
    for game in games:
        writer.writerow(
            [
                game.id_game,
                game.val_event_name,
                game.id_user_white,
                game.id_user_black,
                game.val_result,
                game.val_opening_name,
                game.val_opening_eco_code,
                game.val_site_url,
            ]
        )

    # Return the CSV file as a response with a download header
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=all_games.csv"},
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    session.clear()  # Clear session data to ensure no stale information is present
    db.session.expire_all()  # Force fresh data to avoid using stale queries
    db.session.remove()  # Remove current session to force a new session

    # Step 1: Get total games and valid players
    total_games = Game.query.count()
    total_players = Player.query.filter(
        Player.val_username.notin_(["Anonymous", "BOT", "N/A"]),
        Player.val_username != "",  # Exclude empty usernames
        Player.val_real_name != "",  # Exclude empty real names
    ).count()

    app.logger.debug(
        f"Total Players (after filtering anonymous and large game count): {total_players}"
    )

    # Step 2: Get the true most active player (the one with the highest number of games)
    top_player = (
        db.session.query(Player.val_username, Player.n_games_all, Player.val_url)
        .filter(
            Player.val_username.notin_(["Anonymous", "BOT", "N/A"]),
            Player.val_username != "",  # Ensure player is not empty
            Player.val_real_name != "",  # Ensure player real name is not empty
        )
        .order_by(Player.n_games_all.desc())
        .first()  # Get the player with the most games
    )

    if not top_player:
        top_player_name = "N/A"
        top_player_url = "#"
        top_player_games = 0
    else:
        top_player_name = top_player[0]
        top_player_url = top_player[2]
        top_player_games = top_player[1]

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
        .limit(3)  # Limit to top 3
        .all()
    )

    unique_openings = set()
    most_played_openings = []

    for eco, _ in most_played_eco:
        eco_description = eco_descriptions.get(eco[:2], "Unknown Opening")
        if eco_description not in unique_openings:
            unique_openings.add(eco_description)
            most_played_openings.append(eco_description)

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
        top_player_games=top_player_games,
        most_played_openings=most_played_openings,
    )


@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    # Step 1: Get total games and valid players
    total_games = Game.query.count()
    total_players = Player.query.filter(
        Player.val_username != "Anonymous",  # Exclude players named "Anonymous"
        Player.val_title != "BOT",  # Exclude players with title "BOT"
    ).count()

    # Step 2: Get the true most active player (the one with the highest number of games)
    top_player = (
        db.session.query(
            Player.val_username, Player.n_games_all, Player.val_url, Player.val_title
        )
        .filter(
            Player.val_username
            != "Anonymous",  # Ensure player is not named "Anonymous"
            Player.val_title != "BOT",  # Ensure player is not a bot
        )
        .order_by(Player.n_games_all.desc())
        .first()  # Get the player with the most games
    )

    top_player_name = top_player[0] if top_player else "N/A"
    top_player_url = top_player[2] if top_player else "#"
    top_player_title = (
        top_player[3] if top_player else "N/A"
    )  # Ensure the title is fetched
    top_player_games = top_player[1] if top_player else 0

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
        .limit(3)  # Limit to top 3
        .all()
    )

    # Using a set to store unique openings
    unique_openings = set()
    most_played_openings = []

    for eco, _ in most_played_eco:
        eco_description = eco_descriptions.get(eco[:2], "Unknown Opening")
        if eco_description not in unique_openings:
            unique_openings.add(eco_description)
            most_played_openings.append(eco_description)

    # If fewer than three unique openings, pad with "Unknown Opening"
    while len(most_played_openings) < 3:
        most_played_openings.append("Unknown Opening")

    # Return metrics as JSON
    return jsonify(
        {
            "total_games": total_games,
            "total_players": total_players,
            "top_player": top_player_name,
            "top_player_url": top_player_url,
            "top_player_title": top_player_title,  # Include the player's title here (if needed)
            "top_player_games": top_player_games,
            "most_played_openings": most_played_openings,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
