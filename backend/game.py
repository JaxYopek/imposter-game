import random
import string
from words import CATEGORIES

class Game:
    def __init__(self):
        self.rooms = {}
    
    def create_room(self):
        """Generate a random room code (6 characters for better entropy)"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.rooms[code] = {
            'players': {},
            'word': None,
            'hint': None,
            'imposter_id': None,
            'start_player_id': None,
            'status': 'waiting',  # waiting, collecting_words, playing, round_ended
            'current_round': 0,
            'mode': None,  # 'category' or 'custom_words'
            'submitted_words': {},  # {player_id: word}
            'hints_enabled': False,
        }
        return code
    
    def add_player(self, room_code, player_id, player_name):
        """Add a player to a room"""
        if room_code not in self.rooms:
            return False
        
        self.rooms[room_code]['players'][player_id] = {
            'name': player_name,
            'connected': True,
        }
        return True
    
    def remove_player(self, room_code, player_id):
        """Remove a player from a room"""
        if room_code in self.rooms:
            if player_id in self.rooms[room_code]['players']:
                del self.rooms[room_code]['players'][player_id]
            
            # If no players left, delete the room
            if not self.rooms[room_code]['players']:
                del self.rooms[room_code]
                return True
        return False
    
    def get_room(self, room_code):
        """Get room data"""
        return self.rooms.get(room_code)
    
    def get_players(self, room_code):
        """Get all players in a room"""
        if room_code not in self.rooms:
            return []
        return list(self.rooms[room_code]['players'].items())
    
    def get_word_from_category(self, category):
        """Get a random word from a category"""
        if category not in CATEGORIES:
            return None
        return random.choice(CATEGORIES[category])
    
    def get_categories(self):
        """Get list of all available categories"""
        return list(CATEGORIES.keys())
    
    def start_game(self, room_code, mode, category=None, hints_enabled=False):
        """Start a new round (either with category or custom words mode)"""
        if room_code not in self.rooms:
            return False
        
        room = self.rooms[room_code]
        room['mode'] = mode
        room['current_round'] += 1
        room['submitted_words'] = {}  # Reset submitted words
        room['hints_enabled'] = hints_enabled
        
        # Select random imposter and start player
        player_ids = list(room['players'].keys())
        if player_ids:
            room['imposter_id'] = random.choice(player_ids)
            room['start_player_id'] = random.choice(player_ids)
        
        if mode == 'category':
            # Pick a random word from the category
            if not category:
                return False
            word_data = self.get_word_from_category(category)
            if not word_data:
                return False
            room['word'] = word_data['word']
            room['hint'] = word_data['hint']
            room['status'] = 'playing'
            return True
        
        elif mode == 'custom_words':
            # Wait for players to submit words
            room['status'] = 'collecting_words'
            return True
        
        return False
    
    def submit_word(self, room_code, player_id, word):
        """Player submits a word for custom_words mode"""
        if room_code not in self.rooms:
            return False
        
        room = self.rooms[room_code]
        if room['status'] != 'collecting_words':
            return False
        
        room['submitted_words'][player_id] = word.strip()
        return True
    
    def finalize_custom_words(self, room_code):
        """Select a random word from submitted words and start game"""
        if room_code not in self.rooms:
            return False
        
        room = self.rooms[room_code]
        if not room['submitted_words']:
            return False
        
        # Pick random word from submissions
        words = list(room['submitted_words'].values())
        room['word'] = random.choice(words)
        room['status'] = 'playing'
        
        # Select random imposter and start player
        player_ids = list(room['players'].keys())
        if player_ids:
            room['imposter_id'] = random.choice(player_ids)
            room['start_player_id'] = random.choice(player_ids)
        return True
    
    
    def get_player_view(self, room_code, player_id):
        """Get what a player should see"""
        if room_code not in self.rooms:
            return None
        
        room = self.rooms[room_code]
        is_imposter = player_id == room.get('imposter_id')
        is_start_player = player_id == room.get('start_player_id')
        
        view = {
            'word': 'IMPOSTER' if is_imposter else room['word'],
            'is_imposter': is_imposter,
            'is_start_player': is_start_player,
            'round': room['current_round'],
            'status': room['status'],
        }
        
        # Add hint for imposter if enabled
        if is_imposter and room.get('hints_enabled') and room.get('hint'):
            view['hint'] = room['hint']
        
        return view
    
    def next_round(self, room_code):
        """End current round without starting a new one"""
        if room_code not in self.rooms:
            return False
        
        room = self.rooms[room_code]
        room['status'] = 'waiting'
        room['word'] = None
        room['hint'] = None
        room['imposter_id'] = None
        room['mode'] = None
        room['submitted_words'] = {}
        room['hints_enabled'] = False
        return True

# Global game instance
game = Game()
