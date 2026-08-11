import numpy as np
from PIL import Image, ImageDraw, ImageFont
import random
from typing import List, Tuple, Optional
import copy

class NumberGridPuzzle:
    """
    Number Grid Puzzle - A unique puzzle created by Steven
    Rules: Fill the 6x6 grid with numbers 1-6 such that:
    1. Each row contains numbers 1-6 exactly once
    2. Each column contains numbers 1-6 exactly once
    3. Each 2x3 block contains numbers 1-6 exactly once
    4. The sum of numbers in each diagonal equals 21
    """
    
    def __init__(self):
        self.size = 6
        self.grid = np.zeros((self.size, self.size), dtype=int)
        
    def is_valid(self, grid: np.ndarray, row: int, col: int, num: int) -> bool:
        """Check if placing num at (row, col) is valid"""
        # Check row
        if num in grid[row, :]:
            return False
        
        # Check column
        if num in grid[:, col]:
            return False
        
        # Check 2x3 block
        block_row, block_col = 2 * (row // 2), 3 * (col // 3)
        if num in grid[block_row:block_row+2, block_col:block_col+3]:
            return False
        
        # Check main diagonal sum constraint
        if row == col:
            diag = np.diagonal(grid)
            temp_diag = diag.copy()
            temp_diag[row] = num
            if np.count_nonzero(temp_diag) == 6 and np.sum(temp_diag) != 21:
                return False
        
        # Check anti-diagonal sum constraint
        if row + col == self.size - 1:
            anti_diag = np.fliplr(grid).diagonal()
            temp_anti = anti_diag.copy()
            temp_anti[row] = num
            if np.count_nonzero(temp_anti) == 6 and np.sum(temp_anti) != 21:
                return False
        
        return True
    
    def solve(self, grid: np.ndarray) -> bool:
        """Solve the puzzle using backtracking"""
        empty = self.find_empty(grid)
        if not empty:
            return True
        
        row, col = empty
        for num in range(1, self.size + 1):
            if self.is_valid(grid, row, col, num):
                grid[row, col] = num
                if self.solve(grid):
                    return True
                grid[row, col] = 0
        
        return False
    
    def find_empty(self, grid: np.ndarray) -> Optional[Tuple[int, int]]:
        """Find an empty cell"""
        for i in range(self.size):
            for j in range(self.size):
                if grid[i, j] == 0:
                    return (i, j)
        return None
    
    def generate_solution(self) -> np.ndarray:
        """Generate a complete valid grid"""
        grid = np.zeros((self.size, self.size), dtype=int)
        
        # Fill the grid using backtracking
        for i in range(self.size):
            for j in range(self.size):
                if grid[i, j] == 0:
                    numbers = list(range(1, self.size + 1))
                    random.shuffle(numbers)
                    for num in numbers:
                        if self.is_valid(grid, i, j, num):
                            grid[i, j] = num
                            if self.solve(grid.copy()):
                                break
                            else:
                                grid[i, j] = 0
        
        self.solve(grid)
        return grid
    
    def create_puzzle(self, solution: np.ndarray, difficulty: int) -> np.ndarray:
        """
        Create puzzle by removing cells based on difficulty
        Difficulty 1 (Easy): Remove 40% of cells
        Difficulty 2: Remove 50% of cells
        Difficulty 3: Remove 60% of cells
        Difficulty 4: Remove 70% of cells
        Difficulty 5 (Hardest): Remove 75% of cells with uniqueness constraint
        """
        puzzle = solution.copy()
        
        if difficulty == 1:
            cells_to_remove = int(self.size * self.size * 0.40)
        elif difficulty == 2:
            cells_to_remove = int(self.size * self.size * 0.50)
        elif difficulty == 3:
            cells_to_remove = int(self.size * self.size * 0.60)
        elif difficulty == 4:
            cells_to_remove = int(self.size * self.size * 0.70)
        else:  # difficulty 5 - Hardest
            cells_to_remove = int(self.size * self.size * 0.75)
        
        # For hardest difficulty, ensure unique solution
        if difficulty == 5:
            return self.create_hardest_puzzle(solution)
        
        positions = [(i, j) for i in range(self.size) for j in range(self.size)]
        random.shuffle(positions)
        
        for i, j in positions[:cells_to_remove]:
            puzzle[i, j] = 0
        
        return puzzle
    
    def create_hardest_puzzle(self, solution: np.ndarray) -> np.ndarray:
        """
        Create the hardest puzzle by removing cells while maintaining unique solution
        Uses advanced algorithm to maximize difficulty
        """
        puzzle = solution.copy()
        positions = [(i, j) for i in range(self.size) for j in range(self.size)]
        random.shuffle(positions)
        
        # Remove cells one by one, ensuring unique solution
        removed = 0
        target_removed = int(self.size * self.size * 0.75)
        
        for i, j in positions:
            if removed >= target_removed:
                break
            
            backup = puzzle[i, j]
            puzzle[i, j] = 0
            
            # Count solutions (limit to 2 for efficiency)
            if self.count_solutions(puzzle.copy(), 2) == 1:
                removed += 1
            else:
                puzzle[i, j] = backup
        
        return puzzle
    
    def count_solutions(self, grid: np.ndarray, limit: int) -> int:
        """Count number of solutions up to a limit"""
        empty = self.find_empty(grid)
        if not empty:
            return 1
        
        row, col = empty
        count = 0
        
        for num in range(1, self.size + 1):
            if self.is_valid(grid, row, col, num):
                grid[row, col] = num
                count += self.count_solutions(grid, limit)
                if count >= limit:
                    return count
                grid[row, col] = 0
        
        return count

class PuzzleImageGenerator:
    """Generate JPG images of puzzles and solutions"""
    
    def __init__(self, cell_size=80, margin=40):
        self.cell_size = cell_size
        self.margin = margin
        self.size = 6
        
    def create_image(self, grid: np.ndarray, is_solution: bool = False, difficulty: int = 1) -> Image.Image:
        """Create an image of the puzzle or solution"""
        img_size = self.size * self.cell_size + 2 * self.margin + 200  # Extra space for text
        img = Image.new('RGB', (img_size, img_size + 100), 'white')
        draw = ImageDraw.Draw(img)
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw title
        difficulty_names = {1: "EASY", 2: "MEDIUM", 3: "HARD", 4: "EXPERT", 5: "MASTER"}
        title = f"Number Grid Puzzle - {difficulty_names[difficulty]}"
        if is_solution:
            title += " - SOLUTION"
        draw.text((self.margin, 20), title, fill='black', font=title_font)
        
        # Draw grid
        grid_start_x = self.margin
        grid_start_y = self.margin + 60
        
        # Draw cells
        for i in range(self.size):
            for j in range(self.size):
                x = grid_start_x + j * self.cell_size
                y = grid_start_y + i * self.cell_size
                
                # Draw cell background
                color = 'white' if (i + j) % 2 == 0 else '#f0f0f0'
                draw.rectangle([x, y, x + self.cell_size, y + self.cell_size], 
                             fill=color, outline='black', width=2)
                
                # Draw number
                if grid[i, j] != 0:
                    num_color = 'blue' if is_solution else 'black'
                    text = str(grid[i, j])
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x = x + (self.cell_size - text_width) / 2
                    text_y = y + (self.cell_size - text_height) / 2 - 5
                    draw.text((text_x, text_y), text, fill=num_color, font=font)
        
        # Draw block borders (thicker for 2x3 blocks)
        for i in range(0, self.size + 1, 2):
            y = grid_start_y + i * self.cell_size
            draw.line([(grid_start_x, y), (grid_start_x + self.size * self.cell_size, y)], 
                     fill='black', width=4)
        
        for j in range(0, self.size + 1, 3):
            x = grid_start_x + j * self.cell_size
            draw.line([(x, grid_start_y), (x, grid_start_y + self.size * self.cell_size)], 
                     fill='black', width=4)
        
        # Add Steven's message
        steven_y = grid_start_y + self.size * self.cell_size + 20
        steven_messages = {
            1: "Created by Steven - 'A gentle start to your puzzle journey'",
            2: "Created by Steven - 'The challenge begins to unfold'",
            3: "Created by Steven - 'Only the determined shall proceed'",
            4: "Created by Steven - 'Your logical prowess is tested'",
            5: "Created by Steven - 'The ultimate test of deductive reasoning'"
        }
        draw.text((self.margin, steven_y), steven_messages[difficulty], 
                 fill='darkred', font=small_font)
        
        # Add rules
        rules_y = steven_y + 25
        rules = [
            "Rules:",
            "• Fill each row with numbers 1-6",
            "• Fill each column with numbers 1-6",
            "• Fill each 2x3 block with numbers 1-6",
            "• Main diagonal sums must equal 21"
        ]
        for i, rule in enumerate(rules):
            draw.text((self.margin, rules_y + i * 18), rule, fill='gray', font=small_font)
        
        return img

def generate_all_puzzles():
    """Generate puzzles from easy to hard and save as JPG"""
    puzzle_gen = NumberGridPuzzle()
    img_gen = PuzzleImageGenerator()
    
    # Generate a base solution
    print("Generating base solution...")
    solution = puzzle_gen.generate_solution()
    
    for difficulty in range(1, 6):
        print(f"\nGenerating difficulty {difficulty} puzzle...")
        
        # Create puzzle
        puzzle = puzzle_gen.create_puzzle(solution, difficulty)
        
        # Create images
        puzzle_img = img_gen.create_image(puzzle, is_solution=False, difficulty=difficulty)
        solution_img = img_gen.create_image(solution, is_solution=True, difficulty=difficulty)
        
        # Save images
        puzzle_img.save(f'number_grid_puzzle_level_{difficulty}.jpg', 'JPEG', quality=95)
        solution_img.save(f'number_grid_puzzle_level_{difficulty}_solution.jpg', 'JPEG', quality=95)
        
        # Calculate difficulty metrics
        empty_cells = np.count_nonzero(puzzle == 0)
        total_cells = puzzle.size
        fill_percentage = ((total_cells - empty_cells) / total_cells) * 100
        
        print(f"✓ Level {difficulty} generated:")
        print(f"  - Empty cells: {empty_cells}/{total_cells}")
        print(f"  - Fill percentage: {fill_percentage:.1f}%")
        print(f"  - Saved: number_grid_puzzle_level_{difficulty}.jpg")
        print(f"  - Solution: number_grid_puzzle_level_{difficulty}_solution.jpg")

if __name__ == "__main__":
    print("=" * 60)
    print("NUMBER GRID PUZZLE GENERATOR")
    print("Created by Steven")
    print("=" * 60)
    
    generate_all_puzzles()
    
    print("\n" + "=" * 60)
    print("All puzzles generated successfully!")
    print("Check the current directory for JPG files.")
    print("=" * 60)