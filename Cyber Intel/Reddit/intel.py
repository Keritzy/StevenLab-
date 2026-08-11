#!/usr/bin/env python3
"""
MILITARY-GRADE CIPHER PUZZLE SYSTEM
Advanced multi-layer encryption with puzzle progression
Inspired by Cold War-era cryptographic techniques
"""

import os
import sys
import json
import hashlib
import base64
import random
import string
import time
from datetime import datetime
from typing import Tuple, Dict, List, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import re

# ============================================================
# MILITARY CIPHER ENGINE - CORE CLASS
# ============================================================

class MilitaryCipherEngine:
    """Advanced multi-layer cipher system with puzzle mechanics"""
    
    # NATO phonetic alphabet for encoding
    NATO = {
        'A': 'ALPHA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA',
        'E': 'ECHO', 'F': 'FOXTROT', 'G': 'GOLF', 'H': 'HOTEL',
        'I': 'INDIA', 'J': 'JULIETT', 'K': 'KILO', 'L': 'LIMA',
        'M': 'MIKE', 'N': 'NOVEMBER', 'O': 'OSCAR', 'P': 'PAPA',
        'Q': 'QUEBEC', 'R': 'ROMEO', 'S': 'SIERRA', 'T': 'TANGO',
        'U': 'UNIFORM', 'V': 'VICTOR', 'W': 'WHISKEY', 'X': 'X-RAY',
        'Y': 'YANKEE', 'Z': 'ZULU'
    }
    
    # Reverse NATO mapping
    NATO_REVERSE = {v: k for k, v in NATO.items()}
    
    # Morse code mapping
    MORSE = {
        'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
        'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
        'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
        'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
        'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
        'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
        '3': '...--', '4': '....-', '5': '.....', '6': '-....',
        '7': '--...', '8': '---..', '9': '----.', ' ': '/'
    }
    
    MORSE_REVERSE = {v: k for k, v in MORSE.items()}
    
    # Military rank progression
    RANKS = [
        "PVT (E-1)", "PV2 (E-2)", "PFC (E-3)", "SPC (E-4)",
        "SGT (E-5)", "SSG (E-6)", "SFC (E-7)", "MSG (E-8)",
        "1SG (E-9)", "SGM (E-10)", "CSM (E-11)", "SMA (E-12)",
        "2LT (O-1)", "1LT (O-2)", "CPT (O-3)", "MAJ (O-4)",
        "LTC (O-5)", "COL (O-6)", "BG (O-7)", "MG (O-8)",
        "LTG (O-9)", "GEN (O-10)"
    ]
    
    def __init__(self, key_seed: Optional[str] = None):
        """Initialize with optional key seed"""
        self.key_seed = key_seed or self._generate_key_seed()
        self.salt = b'military_cipher_salt_2024'
        self.fernet_key = self._derive_fernet_key()
        self.cipher = Fernet(self.fernet_key)
        self.operation_history = []
        self.rank_index = 0
        
    def _generate_key_seed(self) -> str:
        """Generate a cryptographically strong key seed"""
        return base64.b64encode(os.urandom(32)).decode('utf-8')
    
    def _derive_fernet_key(self) -> bytes:
        """Derive Fernet key using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.key_seed.encode())
        )
        return key
    
    def _get_current_rank(self) -> str:
        """Get current military rank based on operations count"""
        idx = min(len(self.operation_history) // 3, len(self.RANKS) - 1)
        return self.RANKS[idx]
    
    def _timestamp(self) -> str:
        """Get current timestamp in military format"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ============================================================
    # LAYER 1: CAESAR CIPHER (Variable Shift)
    # ============================================================
    
    def caesar_encrypt(self, text: str, shift: int = None) -> Tuple[str, int]:
        """Caesar cipher with variable shift (1-25)"""
        if shift is None:
            shift = random.randint(1, 25)
        
        result = []
        for char in text.upper():
            if char.isalpha():
                shifted = ord(char) + shift
                if shifted > ord('Z'):
                    shifted -= 26
                result.append(chr(shifted))
            else:
                result.append(char)
        
        encrypted = ''.join(result)
        self.operation_history.append(f"CAESAR({shift})")
        return encrypted, shift
    
    def caesar_decrypt(self, text: str, shift: int) -> str:
        """Decrypt Caesar cipher with known shift"""
        return self.caesar_encrypt(text, -shift)[0]
    
    # ============================================================
    # LAYER 2: VIGENÈRE CIPHER
    # ============================================================
    
    def vigenere_encrypt(self, text: str, key: str = None) -> Tuple[str, str]:
        """Vigenère cipher with generated or provided key"""
        if key is None:
            key = ''.join(random.choices(string.ascii_uppercase, k=12))
        
        key = key.upper()
        result = []
        key_idx = 0
        
        for char in text.upper():
            if char.isalpha():
                shift = ord(key[key_idx % len(key)]) - ord('A')
                shifted = ord(char) + shift
                if shifted > ord('Z'):
                    shifted -= 26
                result.append(chr(shifted))
                key_idx += 1
            else:
                result.append(char)
        
        encrypted = ''.join(result)
        self.operation_history.append(f"VIGENERE(key={key})")
        return encrypted, key
    
    def vigenere_decrypt(self, text: str, key: str) -> str:
        """Decrypt Vigenère cipher"""
        key = key.upper()
        result = []
        key_idx = 0
        
        for char in text.upper():
            if char.isalpha():
                shift = ord(key[key_idx % len(key)]) - ord('A')
                shifted = ord(char) - shift
                if shifted < ord('A'):
                    shifted += 26
                result.append(chr(shifted))
                key_idx += 1
            else:
                result.append(char)
        
        return ''.join(result)
    
    # ============================================================
    # LAYER 3: ADFGVX CIPHER (WWI Military Cipher)
    # ============================================================
    
    def adfgvx_encrypt(self, text: str, key: str = None) -> Tuple[str, str]:
        """
        ADFGVX cipher - used by German military in WWI
        Uses 6x6 Polybius square with A,D,F,G,V,X
        """
        if key is None:
            key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
        
        # Create Polybius square (6x6)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        chars = list(alphabet)
        random.seed(sum(ord(c) for c in key))
        random.shuffle(chars)
        
        # Map characters to coordinates
        coord_map = {}
        for i, char in enumerate(chars):
            coord_map[char] = f"{'ADFGVX'[i//6]}{'ADFGVX'[i%6]}"
        
        # Encrypt each character
        encrypted = ''.join(coord_map.get(c.upper(), '') for c in text if c.isalnum())
        
        # Apply columnar transposition
        cols = len(key)
        rows = (len(encrypted) + cols - 1) // cols
        padded = encrypted.ljust(rows * cols, 'X')
        
        matrix = [list(padded[i*cols:(i+1)*cols]) for i in range(rows)]
        
        # Sort columns by key
        col_order = sorted(range(cols), key=lambda i: key[i])
        
        transposed = []
        for col_idx in col_order:
            for row in matrix:
                transposed.append(row[col_idx])
        
        final = ''.join(transposed)
        self.operation_history.append(f"ADFGVX(key={key[:5]}...)")
        return final, key
    
    def adfgvx_decrypt(self, text: str, key: str) -> str:
        """Decrypt ADFGVX cipher"""
        # Reverse columnar transposition
        cols = len(key)
        rows = len(text) // cols
        
        # Fill matrix column by column based on key order
        col_order = sorted(range(cols), key=lambda i: key[i])
        matrix = [[''] * cols for _ in range(rows)]
        
        idx = 0
        for col_idx in col_order:
            for row in range(rows):
                matrix[row][col_idx] = text[idx]
                idx += 1
        
        # Read row by row
        transposed = ''.join(''.join(row) for row in matrix)
        
        # Reverse Polybius mapping
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        chars = list(alphabet)
        random.seed(sum(ord(c) for c in key))
        random.shuffle(chars)
        
        coord_map = {}
        for i, char in enumerate(chars):
            coord_map[f"{'ADFGVX'[i//6]}{'ADFGVX'[i%6]}"] = char
        
        # Decrypt pairs
        result = []
        for i in range(0, len(transposed), 2):
            pair = transposed[i:i+2]
            if len(pair) == 2 and pair in coord_map:
                result.append(coord_map[pair])
        
        return ''.join(result).rstrip('X')
    
    # ============================================================
    # LAYER 4: ENIGMA-SIMULATOR (ROTOR MACHINE)
    # ============================================================
    
    class EnigmaRotor:
        """Simulates an Enigma machine rotor"""
        def __init__(self, wiring: str, notch: str, offset: int = 0):
            self.wiring = wiring
            self.notch = notch
            self.offset = offset
            self.reverse_wiring = {v: k for k, v in enumerate(wiring)}
        
        def forward(self, char: str) -> str:
            idx = (ord(char) - ord('A') + self.offset) % 26
            return chr((self.wiring[idx] + self.offset) % 26 + ord('A'))
        
        def backward(self, char: str) -> str:
            idx = (ord(char) - ord('A') + self.offset) % 26
            return chr((self.reverse_wiring[idx] + self.offset) % 26 + ord('A'))
        
        def rotate(self) -> bool:
            self.offset = (self.offset + 1) % 26
            return self.offset == ord(self.notch) - ord('A')
    
    def enigma_encrypt(self, text: str, rotor_settings: Tuple = None) -> Tuple[str, dict]:
        """
        Enigma machine simulation with 3 rotors
        Returns encrypted text and settings for decryption
        """
        if rotor_settings is None:
            # Generate random rotor settings
            rotors = [
                "EKMFLGDQVZNTOWYHXUSPAIBRCJ",  # Rotor I
                "AJDKSIRUXBLHWTMCQGZNPYFVOE",  # Rotor II
                "BDFHJLCPRTXVZNYEIWGAKMUSQO"   # Rotor III
            ]
            rotor_notches = ['Q', 'E', 'V']
            offsets = [random.randint(0, 25) for _ in range(3)]
            reflector = "YRUHQSLDPXNGOKMIEBFZCWVJAT"
            rotor_settings = {
                'rotors': rotors,
                'notches': rotor_notches,
                'offsets': offsets,
                'reflector': reflector
            }
        
        # Initialize rotors
        rotors = [
            self.EnigmaRotor(rotor_settings['rotors'][i], 
                           rotor_settings['notches'][i], 
                           rotor_settings['offsets'][i])
            for i in range(3)
        ]
        reflector = rotor_settings['reflector']
        
        result = []
        for char in text.upper():
            if not char.isalpha():
                result.append(char)
                continue
            
            # Rotate rotors (stepping)
            if rotors[1].rotate():
                rotors[2].rotate()
            if rotors[0].rotate():
                rotors[1].rotate()
            
            # Pass through rotors (forward)
            char = rotors[0].forward(char)
            char = rotors[1].forward(char)
            char = rotors[2].forward(char)
            
            # Reflector
            idx = ord(char) - ord('A')
            char = chr((ord(reflector[idx]) - ord('A')) + ord('A'))
            
            # Pass through rotors (backward)
            char = rotors[2].backward(char)
            char = rotors[1].backward(char)
            char = rotors[0].backward(char)
            
            result.append(char)
        
        self.operation_history.append(f"ENIGMA(rotors={rotor_settings['offsets']})")
        return ''.join(result), rotor_settings
    
    def enigma_decrypt(self, text: str, settings: dict) -> str:
        """Decrypt Enigma (same as encrypt, just pass through with same settings)"""
        return self.enigma_encrypt(text, settings)[0]
    
    # ============================================================
    # LAYER 5: NATO MORSE ENCODING
    # ============================================================
    
    def nato_morse_encode(self, text: str) -> str:
        """Encode text to NATO/Morse hybrid"""
        result = []
        for char in text.upper():
            if char in self.NATO:
                morse = self.MORSE.get(char, '')
                result.append(f"[{self.NATO[char]}:{morse}]")
            elif char in self.MORSE:
                result.append(f"[{char}:{self.MORSE[char]}]")
            elif char == ' ':
                result.append(' / ')
            else:
                result.append(char)
        
        return ' '.join(result)
    
    def nato_morse_decode(self, text: str) -> str:
        """Decode from NATO/Morse hybrid"""
        result = []
        parts = text.split('[')
        for part in parts:
            if ']' in part:
                content = part.split(']')[0]
                if ':' in content:
                    code = content.split(':')[1]
                    if code in self.MORSE_REVERSE:
                        result.append(self.MORSE_REVERSE[code])
                    elif content.split(':')[0] in self.NATO_REVERSE:
                        result.append(self.NATO_REVERSE[content.split(':')[0]])
            elif part.strip() and part.strip() != '/':
                result.append(part.strip())
        
        return ''.join(result)
    
    # ============================================================
    # LAYER 6: BOOK CIPHER (SIMULATED)
    # ============================================================
    
    def book_encrypt(self, text: str, book_key: str = None) -> Tuple[str, str]:
        """
        Simulated book cipher using a generated key as page numbers
        """
        if book_key is None:
            book_key = ''.join(random.choices(string.digits, k=20))
        
        # Create coordinate pairs from text
        encrypted = []
        for i, char in enumerate(text):
            if char.isalpha():
                # Use book_key to determine shifts
                shift = int(book_key[i % len(book_key)])
                pos = ord(char.upper()) - ord('A')
                new_pos = (pos + shift) % 26
                encrypted.append(chr(new_pos + ord('A')))
            else:
                encrypted.append(char)
        
        final = ''.join(encrypted)
        self.operation_history.append(f"BOOK(seed={book_key[:5]}...)")
        return final, book_key
    
    def book_decrypt(self, text: str, book_key: str) -> str:
        """Decrypt book cipher"""
        decrypted = []
        for i, char in enumerate(text):
            if char.isalpha():
                shift = int(book_key[i % len(book_key)])
                pos = ord(char.upper()) - ord('A')
                new_pos = (pos - shift) % 26
                decrypted.append(chr(new_pos + ord('A')))
            else:
                decrypted.append(char)
        
        return ''.join(decrypted)
    
    # ============================================================
    # COMPOSITE ENCRYPTION PIPELINE
    # ============================================================
    
    def military_encrypt(self, plaintext: str, difficulty: int = 3) -> Dict:
        """
        Multi-layer military encryption with puzzle generation
        
        difficulty: 1-5 (number of encryption layers)
        """
        if difficulty < 1 or difficulty > 5:
            difficulty = 3
        
        self.operation_history = []
        current = plaintext
        keys = {}
        
        # Generate random salt for each operation
        salt = self._generate_key_seed()[:8]
        keys['salt'] = salt
        
        print(f"\n🔐 MILITARY ENCRYPTION STARTED")
        print(f"📋 Original Message: {plaintext}")
        print(f"🎖️  Current Rank: {self._get_current_rank()}")
        print(f"🎯 Difficulty Level: {difficulty}/5")
        print("-" * 60)
        
        layers = []
        
        # Layer 1: Caesar Shift
        if difficulty >= 1:
            current, shift = self.caesar_encrypt(current)
            keys['caesar_shift'] = shift
            layers.append(f"CAESAR (shift={shift})")
            print(f"🔷 Layer 1 (Caesar): {current[:20]}...")
        
        # Layer 2: Vigenère
        if difficulty >= 2:
            current, vig_key = self.vigenere_encrypt(current)
            keys['vigenere_key'] = vig_key
            layers.append(f"VIGENERE (key={vig_key})")
            print(f"🔶 Layer 2 (Vigenère): {current[:20]}...")
        
        # Layer 3: ADFGVX
        if difficulty >= 3:
            current, adfgvx_key = self.adfgvx_encrypt(current)
            keys['adfgvx_key'] = adfgvx_key
            layers.append(f"ADFGVX (key={adfgvx_key[:5]}...)")
            print(f"🔴 Layer 3 (ADFGVX): {current[:20]}...")
        
        # Layer 4: Enigma
        if difficulty >= 4:
            current, enigma_settings = self.enigma_encrypt(current)
            keys['enigma_settings'] = enigma_settings
            layers.append(f"ENIGMA (offsets={enigma_settings['offsets']})")
            print(f"🟣 Layer 4 (Enigma): {current[:20]}...")
        
        # Layer 5: Book Cipher + NATO/Morse
        if difficulty >= 5:
            current, book_key = self.book_encrypt(current)
            keys['book_key'] = book_key
            layers.append(f"BOOK (key={book_key[:5]}...)")
            print(f"🟢 Layer 5 (Book): {current[:20]}...")
            current = self.nato_morse_encode(current)
            layers.append("NATO-MORSE")
            print(f"⚡ Layer 5b (NATO/Morse): {current[:30]}...")
        
        print("-" * 60)
        print(f"✅ Encryption Complete! {len(layers)} layers applied")
        print(f"🔑 Keys generated: {len(keys)}")
        print()
        
        return {
            'encrypted': current,
            'keys': keys,
            'layers': layers,
            'rank': self._get_current_rank(),
            'timestamp': self._timestamp(),
            'operation_count': len(self.operation_history)
        }
    
    # ============================================================
    # DECRYPTION PIPELINE
    # ============================================================
    
    def military_decrypt(self, encrypted_data: Dict) -> str:
        """
        Decrypt using the keys provided in the encrypted data
        """
        current = encrypted_data['encrypted']
        keys = encrypted_data['keys']
        
        print(f"\n🔓 MILITARY DECRYPTION STARTED")
        print(f"🎖️  Rank Required: {encrypted_data['rank']}")
        print("-" * 60)
        
        # Reverse the layers (last applied, first decrypted)
        
        # Decode NATO/Morse if present
        if 'NATO-MORSE' in encrypted_data.get('layers', []):
            current = self.nato_morse_decode(current)
            print(f"🔓 Decoded NATO/Morse: {current[:20]}...")
        
        # Reverse Book Cipher
        if 'book_key' in keys:
            current = self.book_decrypt(current, keys['book_key'])
            print(f"🔓 Decrypted Book: {current[:20]}...")
        
        # Reverse Enigma
        if 'enigma_settings' in keys:
            current = self.enigma_decrypt(current, keys['enigma_settings'])
            print(f"🔓 Decrypted Enigma: {current[:20]}...")
        
        # Reverse ADFGVX
        if 'adfgvx_key' in keys:
            current = self.adfgvx_decrypt(current, keys['adfgvx_key'])
            print(f"🔓 Decrypted ADFGVX: {current[:20]}...")
        
        # Reverse Vigenère
        if 'vigenere_key' in keys:
            current = self.vigenere_decrypt(current, keys['vigenere_key'])
            print(f"🔓 Decrypted Vigenère: {current[:20]}...")
        
        # Reverse Caesar
        if 'caesar_shift' in keys:
            current = self.caesar_decrypt(current, keys['caesar_shift'])
            print(f"🔓 Decrypted Caesar: {current[:20]}...")
        
        print("-" * 60)
        print(f"✅ Decryption Complete!")
        
        return current
    
    # ============================================================
    # PUZZLE GENERATOR
    # ============================================================
    
    def generate_puzzle(self, message: str, difficulty: int = 3) -> Dict:
        """
        Generate a puzzle with hints for the user to solve
        Military-style training exercise
        """
        # Encrypt the message
        encrypted = self.military_encrypt(message, difficulty)
        
        # Create puzzle hints
        puzzle = {
            'encrypted_text': encrypted['encrypted'],
            'layers_used': encrypted['layers'],
            'hints': self._generate_hints(encrypted),
            'rank_required': encrypted['rank'],
            'timestamp': encrypted['timestamp'],
            'difficulty': difficulty,
            'operation_count': encrypted['operation_count']
        }
        
        return puzzle
    
    def _generate_hints(self, encrypted_data: Dict) -> List[str]:
        """Generate helpful hints for puzzle solving"""
        hints = []
        layers = encrypted_data['layers']
        
        hint_mapping = {
            'CAESAR': "🔑 The Roman emperor's favorite cipher. Try shifting letters.",
            'VIGENERE': "🔑 A French diplomat's cipher. Needs a repeating key.",
            'ADFGVX': "🔑 WWI German military cipher. Only uses 6 letters.",
            'ENIGMA': "🔑 WWII German encryption machine. Complex rotor system.",
            'BOOK': "🔑 Cipher using a book as key. Numbers matter.",
            'NATO-MORSE': "🔑 Military alphabet and dot-dash code."
        }
        
        for layer in layers:
            for key, hint in hint_mapping.items():
                if key in layer.upper():
                    hints.append(hint)
                    break
        
        return hints
    
    # ============================================================
    # REPORT GENERATOR
    # ============================================================
    
    def generate_report(self, operation: Dict) -> str:
        """Generate a military-style report"""
        report = []
        report.append("=" * 70)
        report.append("  🎖️  MILITARY CIPHER OPERATION REPORT")
        report.append("=" * 70)
        report.append(f"  OPERATION ID:     {self._timestamp()}")
        report.append(f"  CURRENT RANK:     {self._get_current_rank()}")
        report.append(f"  TIMESTAMP:        {datetime.now().isoformat()}")
        report.append("-" * 70)
        report.append(f"  LAYERS APPLIED:   {len(operation['layers'])}")
        for i, layer in enumerate(operation['layers'], 1):
            report.append(f"    {i}. {layer}")
        report.append("-" * 70)
        report.append(f"  ENCRYPTED TEXT:   {operation['encrypted'][:50]}...")
        report.append(f"  KEY COUNT:        {len(operation['keys'])}")
        report.append("=" * 70)
        
        return '\n'.join(report)


# ============================================================
# INTERACTIVE COMMAND-LINE INTERFACE
# ============================================================

class MilitaryCipherCLI:
    """Interactive CLI for the Military Cipher Puzzle System"""
    
    def __init__(self):
        self.engine = MilitaryCipherEngine()
        self.running = True
        
    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_banner(self):
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ███╗   ███╗██╗██╗     ████████╗ █████╗ ██████╗ ██╗   ██╗  ║
║   ████╗ ████║██║██║     ╚══██╔══╝██╔══██╗██╔══██╗╚██╗ ██╔╝  ║
║   ██╔████╔██║██║██║        ██║   ███████║██████╔╝ ╚████╔╝   ║
║   ██║╚██╔╝██║██║██║        ██║   ██╔══██║██╔══██╗  ╚██╔╝    ║
║   ██║ ╚═╝ ██║██║███████╗   ██║   ██║  ██║██║  ██║   ██║     ║
║   ╚═╝     ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝     ║
║                                                               ║
║   ADVANCED MILITARY CIPHER PUZZLE SYSTEM v2.0                ║
║   === 6-layer encryption with puzzle mechanics ===           ║
╚═══════════════════════════════════════════════════════════════╝
        """
        print(banner)
        print(f"🎖️  Current Rank: {self.engine._get_current_rank()}")
        print(f"🔑  Key Seed: {self.engine.key_seed[:12]}...")
        print("=" * 70)
    
    def _show_menu(self):
        print("\n📋 OPERATIONS MENU:")
        print("  1. 🔐 Encrypt Message (Military Pipeline)")
        print("  2. 🔓 Decrypt Message")
        print("  3. 🧩 Generate Puzzle (Training Mode)")
        print("  4. 🎯 Solve Puzzle")
        print("  5. 📊 View Operation Report")
        print("  6. 🔄 Reset Engine")
        print("  7. 📖 Show NATO/Morse Reference")
        print("  8. 🚪 Exit")
        print("-" * 70)
    
    def _encrypt_interactive(self):
        print("\n🔐 ENCRYPTION MODE")
        message = input("📝 Enter message to encrypt: ")
        
        print("\nSelect difficulty (1-5):")
        print("  1: Basic (Caesar only)")
        print("  2: Enhanced (+Vigenère)")
        print("  3: Standard (+ADFGVX)")
        print("  4: Advanced (+Enigma)")
        print("  5: Maximum (+Book/NATO)")
        
        try:
            diff = int(input("Choice [3]: ") or "3")
            diff = max(1, min(5, diff))
        except:
            diff = 3
        
        result = self.engine.military_encrypt(message, diff)
        
        print("\n" + "=" * 70)
        print("📦 ENCRYPTED RESULT:")
        print(f"  {result['encrypted']}")
        print("-" * 70)
        print("🔑 KEYS (save for decryption):")
        for key, value in result['keys'].items():
            if key == 'enigma_settings':
                print(f"  {key}: {value['offsets']}")
            else:
                print(f"  {key}: {value}")
        print("=" * 70)
        
        # Save to file
        save = input("\n💾 Save encrypted data to file? (y/n): ").lower()
        if save == 'y':
            filename = f"cipher_operation_{result['timestamp']}.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✅ Saved to {filename}")
        
        return result
    
    def _decrypt_interactive(self):
        print("\n🔓 DECRYPTION MODE")
        source = input("📂 Load from file or enter data? (f/e): ").lower()
        
        if source == 'f':
            filename = input("📁 Enter filename: ")
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded data from {filename}")
            except Exception as e:
                print(f"❌ Error: {e}")
                return
        else:
            print("📝 Enter encrypted data:")
            encrypted_text = input("Text: ")
            
            print("\n🔑 Enter keys (one per line, key=value):")
            print("Example: caesar_shift=5")
            print("Press Enter twice to finish")
            
            keys = {}
            while True:
                line = input("Key: ").strip()
                if not line:
                    break
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k == 'enigma_settings':
                        # Parse enigma settings as offsets
                        offsets = [int(x.strip()) for x in v.split(',')]
                        keys[k] = {'offsets': offsets, 'rotors': [
                            "EKMFLGDQVZNTOWYHXUSPAIBRCJ",
                            "AJDKSIRUXBLHWTMCQGZNPYFVOE", 
                            "BDFHJLCPRTXVZNYEIWGAKMUSQO"
                        ], 'notches': ['Q', 'E', 'V'], 'reflector': "YRUHQSLDPXNGOKMIEBFZCWVJAT"}
                    else:
                        keys[k] = v
            
            data = {
                'encrypted': encrypted_text,
                'keys': keys,
                'layers': ['CAESAR', 'VIGENERE', 'ADFGVX', 'ENIGMA', 'BOOK', 'NATO-MORSE'],
                'rank': 'Unknown',
                'timestamp': self.engine._timestamp(),
                'operation_count': len(keys)
            }
        
        try:
            decrypted = self.engine.military_decrypt(data)
            print("\n" + "=" * 70)
            print("📄 DECRYPTED MESSAGE:")
            print(f"  {decrypted}")
            print("=" * 70)
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
    
    def _generate_puzzle(self):
        print("\n🧩 PUZZLE GENERATOR")
        message = input("📝 Enter secret message: ")
        
        print("\nSelect puzzle difficulty (1-5):")
        diff = int(input("Choice [3]: ") or "3")
        diff = max(1, min(5, diff))
        
        puzzle = self.engine.generate_puzzle(message, diff)
        
        print("\n" + "=" * 70)
        print("🧩 PUZZLE CREATED")
        print("-" * 70)
        print(f"🔐 Encrypted Text:")
        print(f"  {puzzle['encrypted_text']}")
        print("-" * 70)
        print(f"🎯 Difficulty: {puzzle['difficulty']}/5")
        print(f"🎖️  Rank Required: {puzzle['rank_required']}")
        print(f"📋 Layers Used: {', '.join(puzzle['layers_used'])}")
        print("-" * 70)
        print("💡 HINTS:")
        for hint in puzzle['hints']:
            print(f"  {hint}")
        print("=" * 70)
        
        # Save puzzle
        filename = f"puzzle_{puzzle['timestamp']}.json"
        with open(filename, 'w') as f:
            json.dump(puzzle, f, indent=2)
        print(f"✅ Puzzle saved to {filename}")
        
        return puzzle
    
    def _solve_puzzle(self):
        print("\n🎯 SOLVE PUZZLE")
        filename = input("📁 Enter puzzle filename: ")
        
        try:
            with open(filename, 'r') as f:
                puzzle = json.load(f)
            
            print("\n🧩 PUZZLE LOADED")
            print(f"🔐 Encrypted: {puzzle['encrypted_text'][:50]}...")
            print(f"🎯 Difficulty: {puzzle['difficulty']}/5")
            print(f"💡 Hints: {puzzle['hints']}")
            print("\n" + "-" * 70)
            
            print("\n🔑 Enter decryption keys:")
            print("You can solve this manually or use the decrypt function.")
            print("Press Enter to use automated decryption, or manually enter keys.")
            
            manual = input("Manual decryption? (y/n): ").lower()
            
            if manual == 'y':
                print("\n🔑 Enter keys:")
                for layer in puzzle['layers_used']:
                    key = input(f"  {layer} key: ")
                    # Store keys
                print("Manual mode - use the decrypt function with your keys.")
            else:
                # Automated decryption
                data = {
                    'encrypted': puzzle['encrypted_text'],
                    'keys': {
                        'caesar_shift': 5,  # These would need to be derived from the puzzle
                        'vigenere_key': 'SECRETKEY',
                        'adfgvx_key': 'ADFGVXKEY',
                        'enigma_settings': {'offsets': [1, 2, 3]},
                        'book_key': '1234567890'
                    },
                    'layers': puzzle['layers_used'],
                    'rank': puzzle['rank_required'],
                    'timestamp': puzzle['timestamp'],
                    'operation_count': len(puzzle['layers_used'])
                }
                print("\n⚠️  Automated decryption requires the actual keys.")
                print("The keys are stored in the encryption process.")
                
        except Exception as e:
            print(f"❌ Error loading puzzle: {e}")
    
    def _show_reference(self):
        print("\n📖 NATO PHONETIC ALPHABET & MORSE CODE")
        print("-" * 70)
        for letter, code in self.engine.NATO.items():
            morse = self.engine.MORSE.get(letter, '')
            print(f"  {letter} -> {code:10} | {morse}")
        print("-" * 70)
        print("📖 MORSE CODE DIGITS:")
        for digit in '0123456789':
            morse = self.engine.MORSE.get(digit, '')
            print(f"  {digit} -> {morse}")
        print("-" * 70)
        
        print("\n📖 ENIGMA ROTOR SETTINGS:")
        print("  Rotor I:   EKMFLGDQVZNTOWYHXUSPAIBRCJ  (Notch: Q)")
        print("  Rotor II:  AJDKSIRUXBLHWTMCQGZNPYFVOE  (Notch: E)")
        print("  Rotor III: BDFHJLCPRTXVZNYEIWGAKMUSQO  (Notch: V)")
        print("  Reflector: YRUHQSLDPXNGOKMIEBFZCWVJAT")
        print("-" * 70)
    
    def run(self):
        """Main CLI loop"""
        while self.running:
            self._clear_screen()
            self._print_banner()
            self._show_menu()
            
            choice = input("⚡ Select operation: ").strip()
            
            if choice == '1':
                self._encrypt_interactive()
            elif choice == '2':
                self._decrypt_interactive()
            elif choice == '3':
                self._generate_puzzle()
            elif choice == '4':
                self._solve_puzzle()
            elif choice == '5':
                if self.engine.operation_history:
                    report = self.engine.generate_report({
                        'layers': self.engine.operation_history,
                        'keys': {'seed': self.engine.key_seed},
                        'encrypted': 'N/A'
                    })
                    print("\n" + report)
                else:
                    print("\n📊 No operations performed yet.")
            elif choice == '6':
                self.engine = MilitaryCipherEngine()
                print("\n🔄 Engine reset successfully.")
            elif choice == '7':
                self._show_reference()
            elif choice == '8':
                print("\n👋 Exiting Military Cipher System. Stay secure!")
                self.running = False
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
            
            input("\n⏎ Press Enter to continue...")


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    try:
        cli = MilitaryCipherCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\n👋 Operation aborted. Stay secure!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
        sys.exit(1)