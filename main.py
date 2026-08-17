from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

import image_reader


# Allows Pillow to open HEIC and HEIF images
register_heif_opener()

INPUT_FOLDER = Path("Input_images")
CONVERTED_FOLDER = Path("Converted_images")
JPEG_QUALITY = 90


def convert_to_rgb(image):
    """
    Correct phone-camera orientation and safely convert the image to RGB.
    Transparent images receive a white background.
    """
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, "white")
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background

    return image.convert("RGB")


def convert_to_jpg(source_path):
    """
    Convert one image to JPG.

    Existing JPG files are returned without being converted.
    Other formats are saved inside Converted_images.
    """
    if source_path.suffix.lower() == ".jpg":
        return source_path

    # Including the original extension prevents files such as
    # parcel.png and parcel.heic from overwriting each other.
    original_format = source_path.suffix.lower().replace(".", "") or "image"
    output_name = f"{source_path.stem}_{original_format}.jpg"
    output_path = CONVERTED_FOLDER / output_name

    try:
        with Image.open(source_path) as image:
            # Animated images use their first frame
            if getattr(image, "is_animated", False):
                image.seek(0)

            rgb_image = convert_to_rgb(image)

            rgb_image.save(
                output_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
            )

        print(f"Converted: {source_path.name} -> {output_path.name}")
        return output_path

    except UnidentifiedImageError:
        print(f"Skipped: {source_path.name} is not a recognised image.")
    except OSError as error:
        print(f"Could not process {source_path.name}: {error}")

    return None


def process_images():
    if not INPUT_FOLDER.exists():
        print(f"Input folder does not exist: {INPUT_FOLDER}")
        return

    CONVERTED_FOLDER.mkdir(exist_ok=True)

    # Create a fixed list before processing
    files = sorted(
        path
        for path in INPUT_FOLDER.iterdir()
        if path.is_file()
    )

    if not files:
        print("No files found in Input_images.")
        return

    successful = 0
    failed = 0

    for source_path in files:
        jpg_path = convert_to_jpg(source_path)

        if jpg_path is None:
            failed += 1
            continue

        try:
            print(f"\nReading parcel: {source_path.name}")

            image_reader.parcel_reader(str(jpg_path))

            # Only delete after conversion and parcel reading succeed
            if source_path.suffix.lower() in {".heic", ".heif"}:
                source_path.unlink()
                print(f"Deleted original: {source_path.name}")

            successful += 1

        except Exception as error:
            print(f"Parcel reader failed for {source_path.name}: {error}")
            failed += 1

    print("\nProcessing complete")
    print("Successful:", successful)
    print("Failed:", failed)


if __name__ == "__main__":
    process_images()