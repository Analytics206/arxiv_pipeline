import os

# Docker path that should map to your Windows directory
docker_path = "/app/data/pdfs"
print(f"Checking Docker volume mount: {docker_path}")

# Check if the base directory exists
if os.path.exists(docker_path):
    print(f"✅ Base directory exists: {docker_path}")
    # List all subdirectories
    print("\nListing all contents of base directory:")
    for item in os.listdir(docker_path):
        item_path = os.path.join(docker_path, item)
        if os.path.isdir(item_path):
            print(f"📁 Directory: {item} (Contains {len(os.listdir(item_path))} files)")
        else:
            print(f"📄 File: {item}")
            
    # Check for specific category directories
    categories = ["cs.AI", "cs.CV", "cs.LG"]
    print("\nChecking for specific category directories:")
    for category in categories:
        cat_path = os.path.join(docker_path, category)
        if os.path.exists(cat_path):
            print(f"✅ Found: {cat_path} (Contains {len(os.listdir(cat_path))} files)")
            # List a few files for verification
            files = os.listdir(cat_path)
            if files:
                print(f"   Sample files: {', '.join(files[:3])}...")
        else:
            print(f"❌ Missing: {cat_path}")
            
    # Check path permissions
    print("\nChecking directory permissions:")
    try:
        print(f"Read permission: {os.access(docker_path, os.R_OK)}")
        print(f"Write permission: {os.access(docker_path, os.W_OK)}")
        print(f"Execute permission: {os.access(docker_path, os.X_OK)}")
    except Exception as e:
        print(f"Error checking permissions: {e}")
else:
    print(f"❌ Base directory does not exist or is not accessible: {docker_path}")
