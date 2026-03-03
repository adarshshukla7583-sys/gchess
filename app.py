from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = "chess_secret"

# Initialize SocketIO for real-time multiplayer
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

DB_NAME = "database.db"

# ---------- DATABASE CONNECTION ----------
def get_db():
    return sqlite3.connect(DB_NAME)

# ---------- AUTO CREATE TABLE ----------
def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    db.commit()
    db.close()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = cur.fetchone()
        db.close()

        if user:
            session["user"] = u
            return redirect("/dashboard")
        else:
            error = "Incorrect Username or Password!"

    # Note: Ensure login.html is updated to display {{ error }} if it exists
    return render_template("login.html", error=error)

# ---------- SIGNUP ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
            db.commit()
            db.close()
            return redirect("/")
        except sqlite3.IntegrityError:
            error = "Username already exists! Try logging in."

    # Note: Ensure signup.html is updated to display {{ error }} if it exists
    return render_template("signup.html", error=error)

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# ---------- CHESS GAMES ----------
@app.route("/chess/<int:id>")
def chess(id):
    if "user" not in session:
        return redirect("/")

    games = {1: "chess1.html", 2: "chess2.html", 3: "chess3.html", 4: "chess4.html", 5: "chess5.html"}
    template = games.get(id)
    if template:
        return render_template(template)
    return redirect("/dashboard")

# ---------- SMART MATCHMAKING (SOCKET IO) ----------
player_rooms = {} 
waiting_player = None

@socketio.on('join_game')
def handle_join(data):
    global waiting_player
    user = session.get('user', 'Guest')
    
    # If nobody is waiting, put this player in the waiting list
    if waiting_player is None:
        # Create a unique room using their session ID
        room_id = request.sid
        join_room(room_id)
        player_rooms[request.sid] = room_id
        waiting_player = {'sid': request.sid, 'user': user, 'room': room_id}
        
        emit('assign_color', {'color': 'w'})
        emit('player_joined', {'username': user, 'color': 'w'}, room=room_id)
    
    # If someone is already waiting, match them together!
    else:
        room_id = waiting_player['room']
        join_room(room_id)
        player_rooms[request.sid] = room_id
        
        p1 = waiting_player
        p2 = {'sid': request.sid, 'user': user, 'room': room_id}
        
        waiting_player = None # Reset the waiting list for the next players
        
        emit('assign_color', {'color': 'b'})
        
        # Tell both players each other's names
        emit('player_joined', {'username': p2['user'], 'color': 'b'}, room=room_id)
        emit('player_joined', {'username': p1['user'], 'color': 'w'}, to=request.sid)
        
        # Start the game!
        emit('game_ready', {'status': 'start'}, room=room_id)

@socketio.on('send_move')
def handle_move(data):
    room_id = player_rooms.get(request.sid)
    if room_id:
        emit('receive_move', data, room=room_id, include_self=False)

@socketio.on('chat_message')
def handle_chat(data):
    room_id = player_rooms.get(request.sid)
    if room_id:
        emit('new_chat', {'user': session.get('user'), 'msg': data['msg']}, room=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_player
    # If the player who disconnected was the one waiting, clear the waiting list
    if waiting_player and waiting_player['sid'] == request.sid:
        waiting_player = None
    
    room_id = player_rooms.get(request.sid)
    if room_id:
        user = session.get('user', 'Guest')
        emit('game_ready', {'status': 'reconnecting', 'user': user}, room=room_id)
        del player_rooms[request.sid]

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    # Replace '192.168.0.102' with '0.0.0.0' if you want it to automatically 
    # work even if your Wi-Fi router changes your IP tomorrow!
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)