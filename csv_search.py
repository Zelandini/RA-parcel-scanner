import re

import pandas as pd
from rapidfuzz import fuzz


RESIDENTS_CSV = "residents_lookup_enriched_no_spaces.csv"
MINIMUM_NAME_SCORE = 65


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).lower().strip()


def clean_phone(value):
    """Remove spaces, brackets, dashes, and other non-digits."""
    return re.sub(r"\D", "", clean_text(value))


def phones_match(phone_1, phone_2):
    phone_1 = clean_phone(phone_1)
    phone_2 = clean_phone(phone_2)

    if not phone_1 or not phone_2:
        return False

    if phone_1 == phone_2:
        return True

    # Handles local and international formats with different prefixes.
    return len(phone_1) >= 7 and len(phone_2) >= 7 and phone_1[-7:] == phone_2[-7:]


def clean_room_number(value):
    """Keep only room-number digits."""
    digits = re.sub(r"\D", "", clean_text(value))
    return digits.lstrip("0") or digits


def clean_room_letter(value):
    """Return the final letter in a room value, if one exists."""
    letters = re.findall(r"[a-z]", clean_text(value))
    return letters[-1].upper() if letters else ""


def get_aliases(resident):
    aliases = clean_text(resident.get("search_aliases", ""))

    if aliases:
        return [alias.strip() for alias in aliases.split("|") if alias.strip()]

    possible_names = [
        resident.get("search_name", ""),
        resident.get("legal_search_name", ""),
        resident.get("full_name", ""),
        resident.get("legal_full_name", ""),
    ]

    return [clean_text(name) for name in possible_names if clean_text(name)]


def calculate_name_score(resident, search_name):
    aliases = get_aliases(resident)

    if not aliases:
        return 0

    return max(
        max(
            fuzz.ratio(search_name, alias),
            fuzz.token_sort_ratio(search_name, alias),
        )
        for alias in aliases
    )


def resident_details(resident):
    """Convert the resident row into plain values suitable for a report."""
    return {
        "student_id": str(resident.get("student_id", "")),
        "full_name": str(resident.get("full_name", "")),
        "legal_full_name": str(resident.get("legal_full_name", "")),
        "room": str(resident.get("room", "")),
        "building": str(resident.get("building", "")),
        "phone_number": str(resident.get("phone_number", "")),
    }


def search_csv(
    search_name,
    building_number=None,
    room_number=None,
    room_letter=None,
    phone_number=None,
):
    """
    Search for a resident and return a structured result.

    A confirmed result requires exactly one resident whose accepted name alias
    matches the detected name at 100%. Fuzzy and duplicate exact matches are
    returned as unsure so a person can review them.
    """
    df = pd.read_csv(RESIDENTS_CSV, dtype=str, keep_default_na=False)
    detected_name = str(search_name or "").strip()
    normalized_name = clean_text(detected_name)

    if not normalized_name:
        return {
            "status": "not_found",
            "detected_name": detected_name,
            "reason": "No recipient name was detected.",
            "resident": None,
            "name_score": 0.0,
            "evidence": "none",
            "candidates": [],
        }

    results = []

    for index, resident in df.iterrows():
        aliases = get_aliases(resident)
        name_score = calculate_name_score(resident, normalized_name)

        if name_score < MINIMUM_NAME_SCORE:
            continue

        evidence_score = 0
        evidence = []

        if building_number:
            if clean_text(resident.get("building", "")) == clean_text(building_number):
                evidence_score += 8
                evidence.append("building matched")
            else:
                evidence_score -= 4
                evidence.append("building different")

        if room_number:
            csv_room = clean_room_number(resident.get("room_short", ""))
            detected_room = clean_room_number(room_number)

            if csv_room == detected_room:
                evidence_score += 12
                evidence.append("room matched")
            else:
                evidence_score -= 6
                evidence.append("room different")

        if room_letter:
            csv_letter = clean_room_letter(resident.get("room_short", ""))
            detected_letter = clean_room_letter(room_letter)

            if csv_letter == detected_letter:
                evidence_score += 4
                evidence.append("room letter matched")
            else:
                evidence_score -= 2
                evidence.append("room letter different")

        if phone_number:
            if phones_match(resident.get("phone_number", ""), phone_number):
                evidence_score += 15
                evidence.append("phone matched")
            else:
                evidence_score -= 4
                evidence.append("phone different")

        results.append(
            {
                "index": int(index),
                "exact_match": normalized_name in aliases,
                "name_score": round(float(name_score), 1),
                "evidence_score": evidence_score,
                "final_score": round(float(name_score + evidence_score), 1),
                "evidence": ", ".join(evidence) or "name only",
            }
        )

    if not results:
        print("No reliable resident found for:", detected_name)
        return {
            "status": "not_found",
            "detected_name": detected_name,
            "reason": "No resident reached the minimum name similarity.",
            "resident": None,
            "name_score": 0.0,
            "evidence": "none",
            "candidates": [],
        }

    ranked = pd.DataFrame(results).sort_values(
        ["final_score", "name_score"],
        ascending=False,
    )
    best_result = ranked.iloc[0]
    best_resident = df.loc[int(best_result["index"])]

    candidates = []
    for _, candidate_result in ranked.head(3).iterrows():
        candidate_resident = df.loc[int(candidate_result["index"])]
        candidate = resident_details(candidate_resident)
        candidate["name_score"] = float(candidate_result["name_score"])
        candidate["evidence"] = str(candidate_result["evidence"])
        candidates.append(candidate)

    exact_matches = ranked[
        (ranked["exact_match"] == True) & (ranked["name_score"] == 100.0)  # noqa: E712
    ]

    if len(exact_matches) == 1:
        exact_result = exact_matches.iloc[0]
        resident = df.loc[int(exact_result["index"])]
        status = "confirmed"
        reason = "Unique 100% name match."
        selected_result = exact_result
    else:
        resident = best_resident
        status = "unsure"
        selected_result = best_result
        if len(exact_matches) > 1:
            reason = "More than one resident has the same exact name."
        else:
            reason = "The best name match is below 100%."

    details = resident_details(resident)

    print("Confirmed resident match" if status == "confirmed" else "Possible resident match")
    print("Name:", details["full_name"])
    print("Student ID:", details["student_id"])
    print("Room:", details["room"])
    print("Name similarity:", selected_result["name_score"])
    print("Additional evidence:", selected_result["evidence"])

    return {
        "status": status,
        "detected_name": detected_name,
        "reason": reason,
        "resident": details,
        "name_score": float(selected_result["name_score"]),
        "evidence": str(selected_result["evidence"]),
        "candidates": candidates,
    }
