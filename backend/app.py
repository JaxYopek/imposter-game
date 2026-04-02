from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from game import game
import uuid
import os
import re
import logging
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend')
app = Flask(__name__, static_folder=frontend_dir, static_url_path='', template_folder=frontend_dir)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Configure CORS with allowed origins
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    ping_timeout=60,
    ping_interval=25
)

# Rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Store active sessions
sessions = {}

# Input validation helpers
def validate_player_name(name):
    """Validate player name: alphanumeric + spaces, max 20 chars"""
    if not name or not isinstance(name, str):
        return False
    name = name.strip()
    if len(name) < 1 or len(name) > 20:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\s\-_]+$', name))

def validate_word(word):
    """Validate word: alphanumeric + spaces, max 30 chars"""
    if not word or not isinstance(word, str):
        return False
    word = word.strip()
    if len(word) < 1 or len(word) > 30:
        return False
    return bool(re.match(r'^[a-zA-Z0-9\s\-_]+$', word))

@app.route('/')
def index():
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/api/categories')
@limiter.limit("30 per minute")
def get_categories():
    """Get list of available word categories"""
    categories = game.get_categories()
    return jsonify({'categories': categories})

@socketio.on('connect')
def on_connect():
    player_id = str(uuid.uuid4())
    sessions[request.sid] = player_id
    emit('connected', {'player_id': player_id})

@socketio.on('disconnect')
def on_disconnect():
    player_id = sessions.pop(request.sid, None)
    # Note: Room cleanup happens in the 'leave_room' event

@socketio.on('create_room')
def on_create_room(data):
    player_name = data.get('name', 'Anonymous').strip()
    
    # Validate player name
    if not validate_player_name(player_name):
        emit('error', {'message': 'Invalid player name'})
        logger.warning(f'Invalid player name attempt: {player_name}')
        return
    
    room_code = game.create_room()
    player_id = sessions[request.sid]
    
    game.add_player(room_code, player_id, player_name)
    join_room(room_code)
    
    logger.info(f'Room created: {room_code} by {player_name}')
    emit('room_created', {'room_code': room_code}, to=request.sid)
    emit_players_update(room_code)

@socketio.on('join_room')
def on_join_room(data):
    room_code = data.get('room_code', '').upper().strip()
    player_name = data.get('name', 'Anonymous').strip()
    player_id = sessions.get(request.sid)
    
    # Validate player name
    if not validate_player_name(player_name):
        emit('error', {'message': 'Invalid player name'})
        return
    
    room = game.get_room(room_code)
    if not room:
        emit('error', {'message': 'Room not found'})
        logger.warning(f'Join attempt on non-existent room: {room_code}')
        return
    
    if game.add_player(room_code, player_id, player_name):
        join_room(room_code)
        logger.info(f'Player {player_name} joined room {room_code}')
        emit('room_joined', {'room_code': room_code}, to=request.sid)
        emit_players_update(room_code)
    else:
        emit('error', {'message': 'Failed to join room'})

@socketio.on('start_game')
def on_start_game(data):
    room_code = data.get('room_code')
    mode = data.get('mode')  # 'category' or 'custom_words'
    category = data.get('category')
    hints_enabled = data.get('hints_enabled', False)
    
    if mode == 'category':
        if not category:
            emit('error', {'message': 'Please select a category'})
            return
        
        if game.start_game(room_code, mode, category, hints_enabled):
            # Send game view to all players
            players = game.get_players(room_code)
            for pid, player_data in players:
                view = game.get_player_view(room_code, pid)
                emit('game_started', view, to=get_sid_for_player(room_code, pid))
        else:
            emit('error', {'message': 'Failed to start game'})
    
    elif mode == 'custom_words':
        if game.start_game(room_code, mode, hints_enabled=hints_enabled):
            # Notify all players that word collection has started
            socketio.emit('words_collection_started', {}, to=room_code)
        else:
            emit('error', {'message': 'Failed to start word collection'})
    
    else:
        emit('error', {'message': 'Invalid game mode'})

@socketio.on('submit_word')
def on_submit_word(data):
    room_code = data.get('room_code')
    word = data.get('word', '').strip()
    player_id = sessions.get(request.sid)
    
    # Validate word
    if not validate_word(word):
        emit('error', {'message': 'Invalid word'})
        logger.warning(f'Invalid word submission attempt: {word}')
        return
    
    if game.submit_word(room_code, player_id, word):
        # Notify all players that a word was submitted
        room = game.get_room(room_code)
        submitted_count = len(room['submitted_words'])
        total_count = len(room['players'])
        socketio.emit('word_submitted', {
            'submitted': submitted_count,
            'total': total_count
        }, to=room_code)
        
        # Auto-finalize when all players have submitted
        if submitted_count == total_count:
            game.finalize_custom_words(room_code)
            # Send game view to all players
            players = game.get_players(room_code)
            for pid, player_data in players:
                view = game.get_player_view(room_code, pid)
                emit('game_started', view, to=get_sid_for_player(room_code, pid))
    else:
        emit('error', {'message': 'Failed to submit word'})

@socketio.on('finalize_words')
def on_finalize_words(data):
    room_code = data.get('room_code')
    
    if game.finalize_custom_words(room_code):
        # Send game view to all players
        players = game.get_players(room_code)
        for pid, player_data in players:
            view = game.get_player_view(room_code, pid)
            emit('game_started', view, to=get_sid_for_player(room_code, pid))
    else:
        emit('error', {'message': 'Failed to finalize words'}, to=room_code)

@socketio.on('next_round')
def on_next_round(data):
    room_code = data.get('room_code')
    
    if game.next_round(room_code):
        emit('round_ended', {'status': 'waiting_for_host'}, to=room_code)
        emit_players_update(room_code)
    else:
        emit('error', {'message': 'Failed to proceed to next round'})

@socketio.on('leave_room')
def on_leave_room(data):
    room_code = data.get('room_code')
    player_id = sessions.get(request.sid)
    
    leave_room(room_code)
    game.remove_player(room_code, player_id)
    
    # Notify remaining players
    if game.get_room(room_code):
        emit_players_update(room_code)

def emit_players_update(room_code):
    """Emit updated player list to all players in room"""
    players = game.get_players(room_code)
    player_list = [
        {'id': pid, 'name': pdata['name']}
        for pid, pdata in players
    ]
    socketio.emit('players_updated', {'players': player_list}, to=room_code)

def get_sid_for_player(room_code, player_id):
    """Helper to find socket ID for a given player"""
    for sid, pid in sessions.items():
        if pid == player_id:
            return sid
    return None

if __name__ == '__main__':
    flask_env = os.getenv('FLASK_ENV', 'production')
    debug_mode = flask_env == 'development'
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    
    if debug_mode:
        logger.warning('Running in DEVELOPMENT mode')
    
    socketio.run(app, debug=debug_mode, host=host, port=port)
