from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

import image_reader


register_heif_opener()

INPUT_FOLDER = Path("Input_images")
CONVERTED_FOLDER = Path("Converted_images")
OUTPUT_FOLDER = Path("output_lists")
REPORT_PATH = OUTPUT_FOLDER / "parcel_results.txt"
JPEG_QUALITY = 90


def convert_to_rgb(image):
    """Correct orientation and safely convert an image to RGB."""
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, "white")
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background

    return image.convert("RGB")


def convert_to_jpg(source_path):
    """Convert one image to JPG, returning its readable JPG path."""
    if source_path.suffix.lower() == ".jpg":
        return source_path

    original_format = source_path.suffix.lower().replace(".", "") or "image"
    output_path = CONVERTED_FOLDER / f"{source_path.stem}_{original_format}.jpg"

    try:
        with Image.open(source_path) as image:
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


def write_output_report(results):
    """Write confirmed matches first and all review items at the bottom."""
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    confirmed = [result for result in results if result.get("status") == "confirmed"]
    review = [result for result in results if result.get("status") != "confirmed"]

    lines = [
        "PARCEL RESIDENT MATCHES",
        f"Generated: {datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}",
        "",
        "CONFIRMED 100% MATCHES",
        "Student ID | Name | Room Number",
        "-" * 72,
    ]

    if confirmed:
        for result in confirmed:
            resident = result["resident"]
            lines.append(
                f'{resident["student_id"]} | {resident["full_name"]} | {resident["room"]}'
            )
    else:
        lines.append("No confirmed 100% matches.")

    lines.extend(
        [
            "",
            "UNSURE OR NOT FOUND — MANUAL REVIEW REQUIRED",
            "-" * 72,
        ]
    )

    if review:
        for result in review:
            lines.append(f'Image: {result.get("image_file", "Unknown")}')
            lines.append(f'Detected name: {result.get("detected_name") or "Not detected"}')
            lines.append(f'Status: {result.get("status", "error").replace("_", " ").title()}')
            lines.append(f'Reason: {result.get("reason", "Unknown error")}')

            resident = result.get("resident")
            if resident:
                lines.append(
                    "Best candidate: "
                    f'{resident["student_id"]} | {resident["full_name"]} | '
                    f'{resident["room"]} | {result.get("name_score", 0):.1f}%'
                )

            lines.append("")
    else:
        lines.append("No parcels require manual review.")

    REPORT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"\nSaved output report: {REPORT_PATH}")


def error_result(source_path, reason):
    return {
        "status": "error",
        "image_file": source_path.name,
        "detected_name": "",
        "reason": reason,
        "resident": None,
        "name_score": 0.0,
    }


def process_images():
    if not INPUT_FOLDER.exists():
        print(f"Input folder does not exist: {INPUT_FOLDER}")
        return

    CONVERTED_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    files = sorted(path for path in INPUT_FOLDER.iterdir() if path.is_file())

    if not files:
        print("No files found in Input_images.")
        write_output_report([])
        return

    results = []
    successful = 0
    failed = 0

    for source_path in files:
        jpg_path = convert_to_jpg(source_path)

        if jpg_path is None:
            results.append(error_result(source_path, "Image could not be converted to JPG."))
            failed += 1
            continue

        try:
            print(f"\nReading parcel: {source_path.name}")
            result = image_reader.parcel_reader(str(jpg_path))
            result["image_file"] = source_path.name
            results.append(result)

            # Delete the original HEIC/HEIF only after successful processing.
            if source_path.suffix.lower() in {".heic", ".heif"}:
                source_path.unlink()
                print(f"Deleted original: {source_path.name}")

            successful += 1
        except Exception as error:
            print(f"Parcel reader failed for {source_path.name}: {error}")
            results.append(error_result(source_path, str(error)))
            failed += 1

    write_output_report(results)

    print("\nProcessing complete")
    print("Successful:", successful)
    print("Failed:", failed)


if __name__ == "__main__":
    process_images()
