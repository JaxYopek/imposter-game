from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from game import game
import uuid
import os

frontend_dir = os.path.join(os.path.dirname(__file__), '../frontend')
app = Flask(__name__, static_folder=frontend_dir, static_url_path='', template_folder=frontend_dir)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active sessions
sessions = {}

@app.route('/')
def index():
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/api/categories')
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
    player_name = data.get('name', 'Anonymous')
    room_code = game.create_room()
    player_id = sessions[request.sid]
    
    game.add_player(room_code, player_id, player_name)
    join_room(room_code)
    
    emit('room_created', {'room_code': room_code}, to=request.sid)
    emit_players_update(room_code)

@socketio.on('join_room')
def on_join_room(data):
    room_code = data.get('room_code').upper()
    player_name = data.get('name', 'Anonymous')
    player_id = sessions.get(request.sid)
    
    room = game.get_room(room_code)
    if not room:
        emit('error', {'message': 'Room not found'})
        return
    
    if game.add_player(room_code, player_id, player_name):
        join_room(room_code)
        emit('room_joined', {'room_code': room_code}, to=request.sid)
        emit_players_update(room_code)
    else:
        emit('error', {'message': 'Failed to join room'})

@socketio.on('start_game')
def on_start_game(data):
    room_code = data.get('room_code')
    mode = data.get('mode')  # 'category' or 'custom_words'
    category = data.get('category')
    
    if mode == 'category':
        if not category:
            emit('error', {'message': 'Please select a category'})
            return
        
        if game.start_game(room_code, mode, category):
            # Send game view to all players
            players = game.get_players(room_code)
            for pid, player_data in players:
                view = game.get_player_view(room_code, pid)
                emit('game_started', view, to=get_sid_for_player(room_code, pid))
        else:
            emit('error', {'message': 'Failed to start game'})
    
    elif mode == 'custom_words':
        if game.start_game(room_code, mode):
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
    
    if not word:
        emit('error', {'message': 'Word cannot be empty'})
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
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
