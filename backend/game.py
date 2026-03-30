import random
import string
from words import CATEGORIES

class Game:
    def __init__(self):
        self.rooms = {}
    
    def create_room(self):
        """Generate a random room code"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        self.rooms[code] = {
            'players': {},
            'word': None,
            'imposter_id': None,
            'status': 'waiting',  # waiting, collecting_words, playing, round_ended
            'current_round': 0,
            'mode': None,  # 'category' or 'custom_words'
            'submitted_words': {},  # {player_id: word}
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
    
    def start_game(self, room_code, mode, category=None):
        """Start a new round (either with category or custom words mode)"""
        if room_code not in self.rooms:
            return False
        
        room = self.rooms[room_code]
        room['mode'] = mode
        room['current_round'] += 1
        room['submitted_words'] = {}  # Reset submitted words
        
        if mode == 'category':
            # Pick a random word from the category
            if not category:
                return False
            word = self.get_word_from_category(category)
            if not word:
                return False
            room['word'] = word
            room['status'] = 'playing'
            
            # Select random imposter
            player_ids = list(room['players'].keys())
            if player_ids:
                room['imposter_id'] = random.choice(player_ids)
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
        
        # Select random imposter
        player_ids = list(room['players'].keys())
        if player_ids:
            room['imposter_id'] = random.choice(player_ids)
        return True
    
    
    def get_player_view(self, room_code, player_id):
        """Get what a player should see"""
        if room_code not in self.rooms:
            return None
        
        room = self.rooms[room_code]
        is_imposter = player_id == room.get('imposter_id')
        
        return {
            'word': 'IMPOSTER' if is_imposter else room['word'],
            'is_imposter': is_imposter,
            'round': room['current_round'],
            'status': room['status'],
        }
    
    def next_round(self, room_code):
        """End current round without starting a new one"""
        if room_code not in self.rooms:
            return False
        
        room = self.rooms[room_code]
        room['status'] = 'waiting'
        room['word'] = None
        room['imposter_id'] = None
        room['mode'] = None
        room['submitted_words'] = {}
        return True

# Global game instance
game = Game()
