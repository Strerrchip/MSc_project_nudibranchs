packages = [
    "ultralytics",
    "torch",
    "cv2",
    "numpy",
    "PIL",
]

print("Checking SAM-related packages...\n")

for package in packages:
    try:
        __import__(package)
        print(f"FOUND: {package}")
    except ImportError:
        print(f"MISSING: {package}")