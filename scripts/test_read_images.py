from pathlib import Path
from PIL import Image, ImageDraw


# Project root
PROJECT_DIR = Path(__file__).resolve().parents[1]

# Test images
test_images = [
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Aphelodoris_varia/Aphelodoris_varia_img01.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Aphelodoris_varia/Aphelodoris_varia_img02.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img01.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img02.jpg",
    PROJECT_DIR / "raw_data/pilot_images/imagej_test/Doriprismatica_atromarginata/Doriprismatica_atromarginata_img03.jpg",
]

# Output folder
output_dir = PROJECT_DIR / "processed_data/automated_image_analysis/qc_figures"
output_dir.mkdir(parents=True, exist_ok=True)

print("Checking test images...\n")

loaded_images = []

for image_path in test_images:
    if image_path.exists():
        print(f"FOUND: {image_path}")
        img = Image.open(image_path).convert("RGB")
        loaded_images.append((image_path.name, img))
    else:
        print(f"MISSING: {image_path}")

if len(loaded_images) == 0:
    raise FileNotFoundError("No test images were found. Please check file names and extensions.")

# Make simple contact sheet using PIL only
thumb_width = 300
thumb_height = 300
label_height = 50

contact_sheet_width = thumb_width * len(loaded_images)
contact_sheet_height = thumb_height + label_height

contact_sheet = Image.new("RGB", (contact_sheet_width, contact_sheet_height), "white")
draw = ImageDraw.Draw(contact_sheet)

for i, (image_name, img) in enumerate(loaded_images):
    img.thumbnail((thumb_width, thumb_height))

    x = i * thumb_width
    y = label_height

    # Put image in the centre of its box
    img_x = x + (thumb_width - img.width) // 2
    img_y = y + (thumb_height - img.height) // 2

    contact_sheet.paste(img, (img_x, img_y))

    # Add image name
    draw.text((x + 5, 10), image_name, fill="black")

output_path = output_dir / "test_read_images_contact_sheet.png"
contact_sheet.save(output_path)

print("\nSaved QC figure to:")
print(output_path)