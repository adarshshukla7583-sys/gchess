from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3

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

    return render_template("login.html")

# ---------- SIGNUP ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
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
            return "Username already exists"

    return render_template("signup.html")

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
    
    # Agar koi aur wait nahi kar raha, toh is user ko waiting list me daal do
    if waiting_player is None:
        room_id = request.sid
        join_room(room_id)
        player_rooms[request.sid] = room_id
        waiting_player = {'sid': request.sid, 'user': user, 'room': room_id}
        
        emit('assign_color', {'color': 'w'})
        emit('player_joined', {'username': user, 'color': 'w'}, room=room_id)
    
    # Agar pehle se koi wait kar raha hai, toh dono ka naya match kara do
    else:
        room_id = waiting_player['room']
        join_room(room_id)
        player_rooms[request.sid] = room_id
        
        p1 = waiting_player
        p2 = {'sid': request.sid, 'user': user, 'room': room_id}
        waiting_player = None # Agle logon ke liye reset karo
        
        emit('assign_color', {'color': 'b'})
        
        # Dono ko ek doosre ka naam batao
        emit('player_joined', {'username': p2['user'], 'color': 'b'}, room=room_id)
        emit('player_joined', {'username': p1['user'], 'color': 'w'}, to=request.sid)
        
        # Game Start karo!
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
    # Agar waiting wala player bina khele chala gaya, list clear karo
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
from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3

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

    if room not in active_rooms:
        active_rooms[room] = {'w': None, 'b': None}

    assigned_color = 'observer'
    
    # Assign colors based on availability
    if active_rooms[room]['w'] is None:
        active_rooms[room]['w'] = {'sid': request.sid, 'user': user}
        assigned_color = 'w'
    elif active_rooms[room]['b'] is None:
        active_rooms[room]['b'] = {'sid': request.sid, 'user': user}
        assigned_color = 'b'

    # Send the assigned color back to the user
    emit('assign_color', {'color': assigned_color})

    # Broadcast that this player joined
    emit('player_joined', {'username': user, 'color': assigned_color}, room=room)

    # Check if both players are ready
    if active_rooms[room]['w'] is not None and active_rooms[room]['b'] is not None:
        # Tell both clients to hide the loading screen and start
        emit('game_ready', {'status': 'start'}, room=room)
        
        # Sync names so both sides see who they are playing against
        emit('player_joined', {'username': active_rooms[room]['w']['user'], 'color': 'w'}, room=room)
        emit('player_joined', {'username': active_rooms[room]['b']['user'], 'color': 'b'}, room=room)

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
    # If a player disconnects, free up their spot and notify the other player
    for room, players in active_rooms.items():
        if players['w'] is not None and players['w']['sid'] == request.sid:
            user = players['w']['user']
            players['w'] = None
            emit('game_ready', {'status': 'reconnecting', 'user': user}, room=room)
        elif players['b'] is not None and players['b']['sid'] == request.sid:
            user = players['b']['user']
            players['b'] = None
            emit('game_ready', {'status': 'reconnecting', 'user': user}, room=room)

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db() # Create database table if it doesn't exist
    # host="0.0.0.0" allows other devices on your Wi-Fi to connect via your IP
    socketio.run(app, host="192.168.0.102", port=5000, debug=True)