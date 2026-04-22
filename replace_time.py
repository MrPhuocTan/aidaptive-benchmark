import os
import glob

files = glob.glob('src/**/*.py', recursive=True)
for file_path in files:
    with open(file_path, 'r') as f:
        content = f.read()
    
    if 'datetime.utcnow' in content:
        # Add import if missing
        if 'from src.time_utils import get_local_time' not in content:
            # Try to place it after datetime import
            if 'from datetime import' in content:
                content = content.replace('from datetime import', 'from src.time_utils import get_local_time\nfrom datetime import', 1)
            else:
                content = 'from src.time_utils import get_local_time\n' + content
        
        # Replace occurrences
        content = content.replace('datetime.utcnow', 'get_local_time')
        
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated {file_path}")

