// Socket.IO connection
const socket = io();

// Game state
let gameState = {
    playerId: null,
    roomCode: null,
    playerName: null,
    isHost: false,
    isImposter: false,
    isStartPlayer: false,
    currentWord: null,
    currentHint: null,
    players: [],
    roundNumber: 0,
    gameMode: null,  // 'category' or 'custom_words'
    wordSubmitted: false,
    wordSubmitting: false,
    hintsEnabled: false,  // Whether hints are required for custom words
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
    if (!/^[A-Z0-9]{4}$/.test(code)) {
        alert('Room code must be exactly 4 characters');
        return;
    }
    
    gameState.playerName = name;
    socket.emit('join_room', { room_code: code, name });
}

function startGame(mode) {
    // Check that there are at least 2 players
    if (gameState.players.length < 2) {
        alert('You need at least 3 players to start a game');
        return;
    }
    
    if (mode === 'category') {
        const category = document.getElementById('categorySelect').value;
        if (!category) {
            alert('Please select a category');
            return;
        }
        const hintsEnabled = document.getElementById('hintsCheckbox').checked;
        socket.emit('start_game', { room_code: gameState.roomCode, mode: 'category', category, hints_enabled: hintsEnabled });
    } else if (mode === 'custom_words') {
        const hintsEnabled = document.getElementById('customHintsCheckbox').checked;
        gameState.hintsEnabled = hintsEnabled;
        socket.emit('start_game', { room_code: gameState.roomCode, mode: 'custom_words', hints_enabled: hintsEnabled });
    }
}

function selectMode(mode) {
    gameState.gameMode = mode;
    updateModeButtonsState();
    
    // Update UI
    document.getElementById('categorySection').classList.add('hidden');
    document.getElementById('customWordsSection').classList.add('hidden');
    
    if (mode === 'category') {
        document.getElementById('categorySection').classList.remove('hidden');
    } else if (mode === 'custom_words') {
        document.getElementById('customWordsSection').classList.remove('hidden');
    }
}

function updateModeButtonsState() {
    const modeCategoryButton = document.getElementById('modeCategory');
    const modeCustomButton = document.getElementById('modeCustom');

    const categorySelected = gameState.gameMode === 'category';
    const customSelected = gameState.gameMode === 'custom_words';

    modeCategoryButton.classList.toggle('mode-active', categorySelected);
    modeCustomButton.classList.toggle('mode-active', customSelected);

    modeCategoryButton.setAttribute('aria-pressed', categorySelected ? 'true' : 'false');
    modeCustomButton.setAttribute('aria-pressed', customSelected ? 'true' : 'false');
}

function updateWordSubmissionStatus(remaining) {
    const status = document.getElementById('wordSubmissionStatus');
    if (!status) {
        return;
    }

    const parsed = Number(remaining);
    const safeRemaining = Number.isFinite(parsed) ? Math.max(Math.floor(parsed), 0) : 0;
    status.innerHTML = `Players remaining: <span class="remaining-count">${safeRemaining}</span>`;
}

function submitWord() {
    if (gameState.wordSubmitted || gameState.wordSubmitting) {
        return;
    }

    const word = document.getElementById('playerWordInput').value.trim();
    const hint = document.getElementById('playerHintInput').value.trim();
    if (!word) {
        alert('Please enter a word');
        return;
    }
    
    // Check if hints are required
    if (gameState.hintsEnabled && !hint) {
        alert('A hint is required');
        return;
    }

    gameState.wordSubmitting = true;
    const submitButton = document.getElementById('submitWordBtn');
    submitButton.disabled = true;

    socket.emit('submit_word', { room_code: gameState.roomCode, word, hint: hint || null }, (response) => {
        gameState.wordSubmitting = false;

        if (!response || !response.ok) {
            submitButton.disabled = false;
            return;
        }

        gameState.wordSubmitted = true;
        document.getElementById('playerWordInput').disabled = true;
        document.getElementById('playerHintInput').disabled = true;
        submitButton.disabled = true;
    });
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
    gameState.isStartPlayer = data.is_start_player;
    gameState.roundNumber = data.round;
    gameState.currentHint = data.hint || null;
    
    switchScreen('playingScreen');
    updateGameDisplay();
});

socket.on('words_collection_started', (data) => {
    // All players (including host) see the word submission screen
    gameState.hintsEnabled = data.hints_enabled || false;
    switchScreen('wordSubmissionScreen');
    gameState.wordSubmitted = false;
    gameState.wordSubmitting = false;
    document.getElementById('playerWordInput').value = '';
    document.getElementById('playerHintInput').value = '';
    document.getElementById('playerWordInput').disabled = false;
    document.getElementById('playerHintInput').disabled = false;
    document.getElementById('submitWordBtn').disabled = false;
    
    // Update hint input placeholder based on whether hints are required
    const hintInput = document.getElementById('playerHintInput');
    if (gameState.hintsEnabled) {
        hintInput.placeholder = 'Enter a hint';
    } else {
        hintInput.placeholder = 'Enter a hint (optional)';
    }
    
    updateWordSubmissionStatus(gameState.players.length);
});

socket.on('word_submitted', (data) => {
    // Everyone sees submission progress
    const remaining = Math.max(data.total - data.submitted, 0);
    updateWordSubmissionStatus(remaining);
});

socket.on('round_ended', (data) => {
    gameState.gameMode = null;
    gameState.wordSubmitted = false;
    gameState.currentHint = null;
    gameState.isStartPlayer = false;
    gameState.hintsEnabled = false;
    switchScreen('waitingScreen');
    updateHostSection();
    document.getElementById('categorySelect').value = '';
    document.getElementById('hintsCheckbox').checked = false;
    document.getElementById('customHintsCheckbox').checked = false;
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
        document.getElementById('customWordsSection').classList.add('hidden');
        updateModeButtonsState();
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
    
    const startBadge = document.getElementById('startPlayerRole');
    if (gameState.isStartPlayer) {
        startBadge.textContent = 'YOU START';
        startBadge.classList.remove('hidden');
    } else {
        startBadge.classList.add('hidden');
    }
    
    // Show hint for imposter if available
    const hintDisplay = document.getElementById('hintDisplay');
    if (gameState.isImposter && gameState.currentHint) {
        document.getElementById('hintText').textContent = gameState.currentHint;
        hintDisplay.classList.remove('hidden');
    } else {
        hintDisplay.classList.add('hidden');
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
