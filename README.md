# Imposter Game

I created this simple web version of the "Imposter Game" to make it easy to play with my friends (without leaving anyone out!). I will host it soon so that you can play with your friends as well.

## Game Rules

1. One player is randomly selected as the "Imposter"
2. All other players know the secret word
3. The imposter sees "IMPOSTER" instead of the word
4. Players take turns saying one word related to the secret word
5. Goal: Imposter tries to blend in, others try to identify the imposter
6. After discussion, vote on who you think is the imposter

## Setup & Installation

### Backend Setup

1. Navigate to the backend folder:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the Flask server:
```bash
python app.py
```

The server will run on `http://localhost:5000`

### Frontend

The frontend is served automatically by the Flask server. Just visit `http://localhost:5000` in your browser.

## How to Play

1. **Create a Room**: Click "Create Room" and enter your name. You'll get a 6-character room code.
2. **Other Players Join**: Other players enter the room code and their name.
3. **Host Enters Word**: Once everyone has joined, the host enters a word and clicks "Start Game".
4. **Play**: 
   - Everyone sees the word (except the imposter who sees "IMPOSTER")
   - Players take turns saying one word that relates to the secret word
   - After everyone has spoken, discuss and vote on who the imposter is
5. **Next Round**: Click "Next Round" to play again with a new word.

## Tech Stack

- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Backend**: Python Flask, Flask-SocketIO
- **Real-time Communication**: WebSockets via Socket.IO

## File Structure

```
imposter-game/
├── backend/
│   ├── app.py          # Flask server with Socket.IO
│   ├── game.py         # Game logic
│   └── requirements.txt # Python dependencies
└── frontend/
    ├── index.html      # Main HTML
    ├── style.css       # Styles
    └── script.js       # Frontend logic
```

## License

MIT
