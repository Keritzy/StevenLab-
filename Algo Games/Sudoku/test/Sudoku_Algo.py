import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import copy

class SudokuGenerator:
    def __init__(self):
        self.grid = np.zeros((9, 9), dtype=int)
        self.solution = None
        
    def generate_puzzle(self, difficulty='medium'):
        """Generate a Sudoku puzzle with given difficulty"""
        # Create empty grid
        self.grid = np.zeros((9, 9), dtype=int)
        
        # Fill diagonal 3x3 boxes first (they don't affect each other)
        self._fill_diagonal_boxes()
        
        # Solve the rest of the grid
        self._solve_sudoku()
        self.solution = self.grid.copy()
        
        # Remove numbers based on difficulty
        self._remove_numbers(difficulty)
        
        return self.grid, self.solution
    
    def _fill_diagonal_boxes(self):
        """Fill the three diagonal 3x3 boxes"""
        for i in range(0, 9, 3):
            self._fill_box(i, i)
    
    def _fill_box(self, row_start, col_start):
        """Fill a 3x3 box with random numbers"""
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        idx = 0
        for i in range(3):
            for j in range(3):
                self.grid[row_start + i][col_start + j] = numbers[idx]
                idx += 1
    
    def _is_safe(self, row, col, num):
        """Check if placing num at (row, col) is valid"""
        # Check row
        if num in self.grid[row]:
            return False
        
        # Check column
        if num in self.grid[:, col]:
            return False
        
        # Check 3x3 box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if self.grid[box_row + i][box_col + j] == num:
                    return False
        return True
    
    def _solve_sudoku(self):
        """Solve the Sudoku using backtracking"""
        empty = self._find_empty()
        if not empty:
            return True
        
        row, col = empty
        numbers = list(range(1, 10))
        random.shuffle(numbers)
        
        for num in numbers:
            if self._is_safe(row, col, num):
                self.grid[row][col] = num
                if self._solve_sudoku():
                    return True
                self.grid[row][col] = 0
        return False
    
    def _find_empty(self):
        """Find an empty cell"""
        for i in range(9):
            for j in range(9):
                if self.grid[i][j] == 0:
                    return (i, j)
        return None
    
    def _remove_numbers(self, difficulty):
        """Remove numbers based on difficulty level"""
        difficulties = {
            'easy': random.randint(36, 45),      # Keep 36-45 numbers
            'medium': random.randint(27, 35),     # Keep 27-35 numbers
            'hard': random.randint(19, 26),       # Keep 19-26 numbers
            'expert': random.randint(17, 22)      # Keep 17-22 numbers
        }
        
        cells_to_keep = difficulties.get(difficulty, 30)
        cells_to_remove = 81 - cells_to_keep
        
        # Get all positions and shuffle
        positions = [(i, j) for i in range(9) for j in range(9)]
        random.shuffle(positions)
        
        # Remove numbers while ensuring unique solution
        removed = 0
        for pos in positions:
            if removed >= cells_to_remove:
                break
            
            row, col = pos
            backup = self.grid[row][col]
            
            if backup != 0:
                self.grid[row][col] = 0
                
                # Check if solution is still unique
                if self._count_solutions(copy.deepcopy(self.grid)) == 1:
                    removed += 1
                else:
                    self.grid[row][col] = backup
    
    def _count_solutions(self, grid, limit=2):
        """Count number of solutions (up to limit)"""
        def count_helper(grid):
            empty = None
            for i in range(9):
                for j in range(9):
                    if grid[i][j] == 0:
                        empty = (i, j)
                        break
                if empty:
                    break
            
            if not empty:
                return 1
            
            row, col = empty
            count = 0
            
            for num in range(1, 10):
                if self._is_safe_grid(grid, row, col, num):
                    grid[row][col] = num
                    count += count_helper(grid)
                    if count >= limit:
                        return count
                    grid[row][col] = 0
            
            return count
        
        return count_helper(grid)
    
    def _is_safe_grid(self, grid, row, col, num):
        """Check if placing num is valid in given grid"""
        # Check row
        if num in grid[row]:
            return False
        
        # Check column
        if num in grid[:, col]:
            return False
        
        # Check box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if grid[box_row + i][box_col + j] == num:
                    return False
        return True


class SudokuImageRenderer:
    def __init__(self, cell_size=60):
        self.cell_size = cell_size
        self.width = cell_size * 9
        self.height = cell_size * 9
        
        # Try to load a nice font, fall back to default
        try:
            self.font = ImageFont.truetype("arial.ttf", size=cell_size//2)
            self.small_font = ImageFont.truetype("arial.ttf", size=cell_size//4)
        except:
            self.font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
    
    def create_puzzle_image(self, puzzle, difficulty="medium", show_title=True):
        """Create an image of the Sudoku puzzle"""
        # Add extra space for title
        extra_height = 80 if show_title else 0
        img = Image.new('RGB', (self.width, self.height + extra_height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw title
        if show_title:
            title = f"Sudoku Puzzle - {difficulty.upper()}"
            # Calculate text position (center)
            try:
                title_font = ImageFont.truetype("arial.ttf", size=30)
            except:
                title_font = ImageFont.load_default()
            
            # Get text bounding box for centering
            bbox = draw.textbbox((0, 0), title, font=title_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, 20), title, fill='black', font=title_font)
        
        # Draw grid lines
        offset_y = extra_height
        
        for i in range(10):
            line_width = 3 if i % 3 == 0 else 1
            # Horizontal lines
            draw.line([(0, offset_y + i * self.cell_size), 
                      (self.width, offset_y + i * self.cell_size)], 
                     fill='black', width=line_width)
            # Vertical lines
            draw.line([(i * self.cell_size, offset_y), 
                      (i * self.cell_size, offset_y + self.height)], 
                     fill='black', width=line_width)
        
        # Draw numbers
        for i in range(9):
            for j in range(9):
                if puzzle[i][j] != 0:
                    x = j * self.cell_size + self.cell_size // 3
                    y = offset_y + i * self.cell_size + self.cell_size // 4
                    draw.text((x, y), str(puzzle[i][j]), 
                             fill='black', font=self.font)
        
        return img
    
    def create_solution_image(self, puzzle, solution):
        """Create an image showing both puzzle and solution"""
        cell_size = self.cell_size
        img = Image.new('RGB', (self.width * 2 + 40, self.height + 100), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw titles
        try:
            title_font = ImageFont.truetype("arial.ttf", size=24)
        except:
            title_font = ImageFont.load_default()
        
        draw.text((self.width//4, 10), "PUZZLE", fill='black', font=title_font)
        draw.text((self.width + 40 + self.width//4, 10), "SOLUTION", 
                 fill='black', font=title_font)
        
        # Draw puzzle
        for i in range(10):
            line_width = 3 if i % 3 == 0 else 1
            y = 50 + i * cell_size
            draw.line([(0, y), (self.width, y)], fill='black', width=line_width)
            draw.line([(i * cell_size, 50), (i * cell_size, 50 + self.height)], 
                     fill='black', width=line_width)
        
        # Draw solution
        offset_x = self.width + 40
        for i in range(10):
            line_width = 3 if i % 3 == 0 else 1
            y = 50 + i * cell_size
            draw.line([(offset_x, y), (offset_x + self.width, y)], 
                     fill='black', width=line_width)
            draw.line([(offset_x + i * cell_size, 50), 
                      (offset_x + i * cell_size, 50 + self.height)], 
                     fill='black', width=line_width)
        
        # Draw numbers
        for i in range(9):
            for j in range(9):
                # Puzzle numbers
                if puzzle[i][j] != 0:
                    x = j * cell_size + cell_size // 3
                    y = 50 + i * cell_size + cell_size // 4
                    draw.text((x, y), str(puzzle[i][j]), 
                             fill='black', font=self.font)
                
                # Solution numbers (show all in blue, different color for given)
                x = offset_x + j * cell_size + cell_size // 3
                y = 50 + i * cell_size + cell_size // 4
                color = 'black' if puzzle[i][j] != 0 else 'blue'
                draw.text((x, y), str(solution[i][j]), 
                         fill=color, font=self.font)
        
        return img
    
    def save_puzzle(self, puzzle, difficulty, filename=None):
        """Save puzzle as image file"""
        if filename is None:
            filename = f"sudoku_{difficulty}.png"
        
        img = self.create_puzzle_image(puzzle, difficulty)
        img.save(filename)
        print(f"Puzzle saved as {filename}")
        return filename


def main():
    """Main function to generate and save Sudoku puzzles"""
    print("Sudoku Puzzle Generator")
    print("=" * 30)
    
    # Create generator and renderer
    generator = SudokuGenerator()
    renderer = SudokuImageRenderer(cell_size=60)
    
    while True:
        print("\nChoose difficulty:")
        print("1. Easy")
        print("2. Medium")
        print("3. Hard")
        print("4. Expert")
        print("5. Generate all difficulties")
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == '6':
            print("Goodbye!")
            break
        
        difficulties = {
            '1': 'easy',
            '2': 'medium',
            '3': 'hard',
            '4': 'expert'
        }
        
        if choice == '5':
            generate_list = ['easy', 'medium', 'hard', 'expert']
        elif choice in difficulties:
            generate_list = [difficulties[choice]]
        else:
            print("Invalid choice. Please try again.")
            continue
        
        for diff in generate_list:
            print(f"\nGenerating {diff} puzzle...")
            puzzle, solution = generator.generate_puzzle(diff)
            
            # Save puzzle image
            puzzle_filename = f"sudoku_{diff}.png"
            renderer.save_puzzle(puzzle, diff, puzzle_filename)
            
            # Save solution image
            solution_filename = f"sudoku_{diff}_solution.png"
            solution_img = renderer.create_solution_image(puzzle, solution)
            solution_img.save(solution_filename)
            print(f"Solution saved as {solution_filename}")
            
            # Print puzzle to console
            print(f"\n{diff.upper()} Puzzle:")
            print("-" * 25)
            for row in puzzle:
                print(" ".join(str(num) if num != 0 else "." for num in row))
            
            # Count given numbers
            given_count = np.count_nonzero(puzzle)
            print(f"\nGiven numbers: {given_count}/81")
        
        if choice != '5':
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()