packages = [
    "PIL",
    "numpy",
    "pandas",
    "cv2",
    "skimage",
    "matplotlib",
]

print("Checking image-analysis Python packages...\n")

for package in packages:
    try:
        __import__(package)
        print(f"FOUND: {package}")
    except ImportError:
        print(f"MISSING: {package}")