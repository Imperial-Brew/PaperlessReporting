"""
Test script to verify that the UsersPuller class and async main() function
can be imported from scripts/pull_users.py.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

try:
    from scripts.pull_users import UsersPuller, main
    print("✅ Successfully imported UsersPuller and main from scripts.pull_users")
    print(f"UsersPuller type: {type(UsersPuller)}")
    print(f"main type: {type(main)}")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

print("All imports successful!")