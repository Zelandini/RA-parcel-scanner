import base64
from typing import Literal, Optional

from google import genai
from pydantic import BaseModel, Field

from csv_search import search_csv


def parcel_reader(image_file):
    with open(image_file, "rb") as file:
        image_bytes = file.read()

    client = genai.Client()

    prompt = """
    You are reading a parcel delivery label.

    Identify the intended recipient of the parcel and extract the
    delivery information.

    Return the following fields:

    - recipient_full_name
    - raw_room_text
    - building_number
    - room_number
    - room_letter
    - building_or_residence_name
    - delivery_address
    - tracking_number
    - confidence

    Room-standardisation rules:

    1. raw_room_text:
       - Preserve the room, unit or apartment text exactly as visible.
       - Return null if no internal room information is clearly visible.

    2. building_number:
       - Return only one of: 831, 832, 833, 834, 835, 836 or 837.
       - Only return it when explicitly visible as part of the
         accommodation building or room identifier.
       - Do not guess the building.
       - Do not use a street number, postcode or unrelated number.

    3. room_number:
       - Return only the numeric internal room portion.
       - Do not include the building number or room letter.
       - Do not use street numbers, postcodes, phone numbers or
         tracking numbers.

    4. room_letter:
       - Return only the final room letter in uppercase.
       - If no room letter is visible, return null.

    Examples:

    Visible room: "837-101A"
    building_number: "837"
    room_number: "101"
    room_letter: "A"
    raw_room_text: "837-101A"

    Visible room: "Room 101A"
    building_number: null
    room_number: "101"
    room_letter: "A"
    raw_room_text: "Room 101A"

    Visible room: "Unit 101"
    building_number: null
    room_number: "101"
    room_letter: null
    raw_room_text: "Unit 101"

    Visible text: "1685 Queen Street"
    This is a street address, not an internal room.
    building_number: null
    room_number: null
    room_letter: null
    raw_room_text: null

    Important rules:

    - Identify the recipient, not the sender or return-address contact.
    - Do not guess missing information.
    - Return null when a field is not clearly visible.
    - Preserve the recipient's spelling as displayed.
    - If multiple recipient names are possible, select the most likely
      recipient and set confidence to low.
    - Confidence must be high, medium or low.
    """

    class ParcelResult(BaseModel):
        recipient_full_name: Optional[str] = Field(
            default=None,
            description="Full name of the intended parcel recipient.",
        )
        raw_room_text: Optional[str] = Field(
            default=None,
            description="Room, unit or apartment text exactly as displayed.",
        )
        building_number: Optional[
            Literal["831", "832", "833", "834", "835", "836", "837"]
        ] = Field(
            default=None,
            description="Explicit CPSV building number, without guessing.",
        )
        room_number: Optional[str] = Field(
            default=None,
            pattern=r"^\d+$",
            description="Numeric internal room portion without building or letter.",
        )
        room_letter: Optional[str] = Field(
            default=None,
            pattern=r"^[A-Z]$",
            description="Optional single uppercase room letter.",
        )
        building_or_residence_name: Optional[str] = Field(
            default=None,
            description="Building or residence name exactly as displayed.",
        )
        delivery_address: Optional[str] = Field(
            default=None,
            description="Visible delivery address.",
        )
        tracking_number: Optional[str] = Field(
            default=None,
            description="Visible parcel tracking number.",
        )
        confidence: Literal["high", "medium", "low"]

    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=[
            {"type": "text", "text": prompt},
            {
                "type": "image",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": "image/jpeg",
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ParcelResult.model_json_schema(),
        },
    )

    result = ParcelResult.model_validate_json(interaction.output_text)
    print(result.model_dump_json(indent=2))
    print()

    if result.recipient_full_name:
        match_result = search_csv(
            search_name=result.recipient_full_name,
            building_number=result.building_number,
            room_number=result.room_number,
            room_letter=result.room_letter,
        )
    else:
        print("No recipient name was detected.")
        match_result = {
            "status": "not_found",
            "detected_name": "",
            "reason": "No recipient name was detected on the parcel.",
            "resident": None,
            "name_score": 0.0,
            "evidence": "none",
            "candidates": [],
        }

    match_result["gemini_confidence"] = result.confidence
    match_result["raw_room_text"] = result.raw_room_text
    match_result["tracking_number"] = result.tracking_number
    return match_result
