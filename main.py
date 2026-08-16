import base64
from google import genai
from typing import Optional, Literal
from pydantic import BaseModel
from csv_search import search_csv

with open('IMG_9911.jpg', 'rb') as f:
    image_bytes = f.read()

client = genai.Client()

prompt = """You are reading a parcel delivery label.

Identify the intended recipient of the parcel.

Return:
- recipient_full_name
- room_number, apartment_number, or unit_number if clearly visible
- building_or_residence_name if clearly visible
- delivery_address if clearly visible
- tracking_number if clearly visible
- confidence: high, medium, or low

Important rules:
- Identify the recipient, NOT the sender or return address.
- Do not guess missing information.
- If a field is not clearly visible, return null.
- Preserve the spelling shown on the label.
- If there are multiple possible recipient names, choose the most likely recipient and set confidence to low.

Return only JSON in this format:

{
  "recipient_full_name": null,
  "room_number": null,
  "building_or_residence_name": null,
  "delivery_address": null,
  "tracking_number": null,
  "confidence": "low"
}"""

class ParcelResult(BaseModel):
    recipient_full_name: Optional[str]
    room_number: Optional[str]
    building_or_residence_name: Optional[str]
    delivery_address: Optional[str]
    tracking_number: Optional[str]
    confidence: Literal["high", "medium", "low"]


interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input=[
        {"type": "text", "text": prompt},
        {
            "type": "image",
            "data": base64.b64encode(image_bytes).decode('utf-8'),
            "mime_type": "image/jpeg"
        }
    ],
    response_format={
        "type": "text",
        "mime_type": "application/json",
        "schema": ParcelResult.model_json_schema()
    },
)
result = ParcelResult.model_validate_json(interaction.output_text)

if result.recipient_full_name:
    search_name = result.recipient_full_name.lower().strip()
    search_csv(search_name)