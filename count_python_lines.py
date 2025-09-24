import os

# Set the root directory to the current directory
root_dir = os.path.dirname(os.path.abspath(__file__))

file_line_counts = []

for dirpath, dirnames, filenames in os.walk(root_dir):
    # Skip __pycache__ folders
    dirnames[:] = [d for d in dirnames if d != '__pycache__']
    for filename in filenames:
        if filename.endswith('.py'):
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                file_line_counts.append((file_path, len(lines)))
            except Exception as e:
                file_line_counts.append((file_path, f'Error: {e}'))

# Sort by line count descending
file_line_counts.sort(key=lambda x: (x[1] if isinstance(x[1], int) else -1), reverse=True)

for file_path, line_count in file_line_counts:
    print(f'{file_path}: {line_count}')

total = sum(lc for _, lc in file_line_counts if isinstance(lc, int))
print(f'\nTotal lines in all Python files: {total}')
