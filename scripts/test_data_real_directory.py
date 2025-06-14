import os
import sys
import time

def test_data_real_directory():
    """
    Test if the data_real directory exists and is writable.
    """
    # Get the project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_real_dir = os.path.join(project_root, "data_real")
    
    print(f"Testing data_real directory: {data_real_dir}")
    
    # Check if directory exists
    if os.path.exists(data_real_dir):
        print(f"✓ Directory exists: {data_real_dir}")
    else:
        print(f"✗ Directory does not exist: {data_real_dir}")
        try:
            os.makedirs(data_real_dir, exist_ok=True)
            print(f"✓ Created directory: {data_real_dir}")
        except Exception as e:
            print(f"✗ Failed to create directory: {str(e)}")
            return False
    
    # Check if directory is writable by creating a test file
    test_file = os.path.join(data_real_dir, f"test_write_{int(time.time())}.txt")
    try:
        with open(test_file, 'w') as f:
            f.write(f"Test file created at {time.ctime()}\n")
        print(f"✓ Successfully wrote to test file: {test_file}")
        
        # Verify the file exists
        if os.path.exists(test_file):
            print(f"✓ Verified file exists: {test_file}")
            print(f"✓ File size: {os.path.getsize(test_file)} bytes")
            
            # List all files in the directory
            print(f"\nFiles in {data_real_dir}:")
            for filename in os.listdir(data_real_dir):
                file_path = os.path.join(data_real_dir, filename)
                file_size = os.path.getsize(file_path)
                file_time = time.ctime(os.path.getmtime(file_path))
                print(f"  - {filename} ({file_size} bytes, modified: {file_time})")
            
            # Clean up
            os.remove(test_file)
            print(f"✓ Removed test file: {test_file}")
        else:
            print(f"✗ File does not exist after writing: {test_file}")
            return False
    except Exception as e:
        print(f"✗ Failed to write to file: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_data_real_directory()
    sys.exit(0 if success else 1)