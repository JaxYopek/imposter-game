// Socket.IO connection
const socket = io();

// Game state
let gameState = {
    playerId: null,
    roomCode: null,
    playerName: null,
    isHost: false,
    isImposter: false,
    currentWord: null,
    players: [],
    roundNumber: 0,
    gameMode: null,  // 'category' or 'custom_words'
    wordSubmitted: false,
};

// Load categories on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
});

// Connect event
socket.on('connected', (data) => {
    gameState.playerId = data.player_id;
    console.log('Connected with player ID:', gameState.playerId);
});

// Error handling
socket.on('error', (data) => {
    alert(data.message);
});

// UI Functions
function switchScreen(screenName) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenName).classList.add('active');
}

function loadCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('categorySelect');
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading categories:', error));
}

function toggleJoinForm() {
    const form = document.getElementById('joinForm');
    form.classList.toggle('hidden');
}

function createRoom() {
    const name = document.getElementById('playerName').value.trim();
    if (!name) {
        alert('Please enter your name');
        return;
    }
    gameState.playerName = name;
    gameState.isHost = true;
    socket.emit('create_room', { name });
}

function joinRoom() {
    const name = document.getElementById('playerName').value.trim();
    const code = document.getElementById('roomCode').value.trim().toUpperCase();
    
    if (!name) {
        alert('Please enter your name');
        return;
    }
    if (!code) {
        alert('Please enter a room code');
        return;
    }
    
    gameState.playerName = name;
    socket.emit('join_room', { room_code: code, name });
}

function startGame() {
    const category = document.getElementById('categorySelect').value;
    if (!category) {
        alert('Please select a category');
        return;
    }
    socket.emit('start_game', { room_code: gameState.roomCode, mode: 'category', category });
}

function selectMode(mode) {
    gameState.gameMode = mode;
    
    // Update UI
    document.getElementById('categorySection').classList.add('hidden');
    
    if (mode === 'category') {
        document.getElementById('categorySection').classList.remove('hidden');
        document.getElementById('modeCategory').disabled = true;
        document.getElementById('modeCustom').disabled = false;
    } else if (mode === 'custom_words') {
        document.getElementById('modeCustom').disabled = true;
        document.getElementById('modeCategory').disabled = false;
        socket.emit('start_game', { room_code: gameState.roomCode, mode: 'custom_words' });
    }
}

function submitWord() {
    const word = document.getElementById('playerWordInput').value.trim();
    if (!word) {
        alert('Please enter a word');
        return;
    }
    socket.emit('submit_word', { room_code: gameState.roomCode, word });
    gameState.wordSubmitted = true;
    document.getElementById('playerWordInput').disabled = true;
}

function nextRound() {
    socket.emit('next_round', { room_code: gameState.roomCode });
}

function leaveRoom() {
    socket.emit('leave_room', { room_code: gameState.roomCode });
    gameState.roomCode = null;
    gameState.isHost = false;
    switchScreen('joinScreen');
    document.getElementById('joinForm').classList.add('hidden');
    document.getElementById('categorySelect').value = '';
}

// Socket events
socket.on('room_created', (data) => {
    gameState.roomCode = data.room_code;
    document.getElementById('displayRoomCode').textContent = gameState.roomCode;
    switchScreen('waitingScreen');
    updateHostSection();
});

socket.on('room_joined', (data) => {
    gameState.roomCode = data.room_code;
    document.getElementById('displayRoomCode').textContent = gameState.roomCode;
    switchScreen('waitingScreen');
    updateHostSection();
});

socket.on('players_updated', (data) => {
    gameState.players = data.players;
    updatePlayersList();
});

socket.on('game_started', (data) => {
    gameState.currentWord = data.word;
    gameState.isImposter = data.is_imposter;
    gameState.roundNumber = data.round;
    
    switchScreen('playingScreen');
    updateGameDisplay();
});

socket.on('words_collection_started', (data) => {
    // All players (including host) see the word submission screen
    switchScreen('wordSubmissionScreen');
    gameState.wordSubmitted = false;
    document.getElementById('playerWordInput').value = '';
    document.getElementById('playerWordInput').disabled = false;
});

socket.on('word_submitted', (data) => {
    // Host sees submission progress
    const status = document.getElementById('wordSubmissionStatus');
    status.textContent = `${data.submitted}/${data.total} players submitted`;
    
    // If all players have submitted, show finalize button
    if (data.submitted === data.total) {
        document.getElementById('finalizeBtn').classList.remove('hidden');
    }
});

socket.on('round_ended', (data) => {
    switchScreen('waitingScreen');
    updateHostSection();
    document.getElementById('categorySelect').value = '';
    gameState.gameMode = null;
    gameState.wordSubmitted = false;
});

// Update functions
function updatePlayersList() {
    const list = document.getElementById('playersList');
    const gameList = document.getElementById('gamePlayersList');
    
    let html = '';
    gameState.players.forEach(player => {
        html += `<li>${player.name}</li>`;
    });
    
    list.innerHTML = html;
    gameList.innerHTML = html;
}

function updateHostSection() {
    const section = document.getElementById('hostSection');
    if (gameState.isHost) {
        section.classList.remove('hidden');
        // Reset mode selection UI
        document.getElementById('categorySection').classList.add('hidden');
        document.getElementById('modeCategory').disabled = false;
        document.getElementById('modeCustom').disabled = false;
    } else {
        section.classList.add('hidden');
    }
}

function updateGameDisplay() {
    document.getElementById('roundNumber').textContent = gameState.roundNumber;
    document.getElementById('wordOrImposter').textContent = gameState.currentWord;
    
    const roleBadge = document.getElementById('playerRole');
    if (gameState.isImposter) {
        roleBadge.textContent = 'YOU ARE THE IMPOSTER!';
        roleBadge.classList.add('imposter-badge');
        roleBadge.classList.remove('hidden');
    } else {
        roleBadge.classList.add('hidden');
    }
    
    // Only show Next Round button for host
    const nextRoundSection = document.getElementById('nextRoundSection');
    if (gameState.isHost) {
        nextRoundSection.classList.remove('hidden');
    } else {
        nextRoundSection.classList.add('hidden');
    }
    
    updatePlayersList();
}
