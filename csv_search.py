import re
import pandas as pd
from rapidfuzz import fuzz


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).lower().strip()


def clean_phone(value):
    """Remove spaces, brackets, dashes, etc."""
    return re.sub(r"\D", "", clean_text(value))


def phones_match(phone_1, phone_2):
    phone_1 = clean_phone(phone_1)
    phone_2 = clean_phone(phone_2)

    if not phone_1 or not phone_2:
        return False

    # Exact match
    if phone_1 == phone_2:
        return True

    # Allows formats such as:
    # 021 123 4567 and +64 21 123 4567
    return phone_1[-7:] == phone_2[-7:]


def clean_room_number(value):
    """Keep only room-number digits."""
    digits = re.sub(r"\D", "", clean_text(value))
    return digits.lstrip("0") or digits


def clean_room_letter(value):
    """Keep only the room letter."""
    return re.sub(r"[^a-z]", "", clean_text(value)).upper()


def get_aliases(resident):
    aliases = clean_text(resident.get("search_aliases", ""))

    if aliases:
        return [alias.strip() for alias in aliases.split("|") if alias.strip()]

    # Fallback when search_aliases is unavailable
    possible_names = [
        resident.get("search_name", ""),
        resident.get("legal_search_name", ""),
        resident.get("full_name", ""),
        resident.get("legal_full_name", ""),
    ]

    return [
        clean_text(name)
        for name in possible_names
        if clean_text(name)
    ]


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


def search_csv(
    search_name,
    building_number=None,
    room_number=None,
    room_letter=None,
    phone_number=None,
):
    df = pd.read_csv(
        "residents_lookup_enriched_no_spaces.csv",
        dtype=str,
        keep_default_na=False,
    )

    search_name = clean_text(search_name)

    results = []

    for index, resident in df.iterrows():
        name_score = calculate_name_score(resident, search_name)

        # Name remains the main requirement
        if name_score < 65:
            continue

        evidence_score = 0
        evidence = []

        # Building check
        if building_number:
            if clean_text(resident["building"]) == clean_text(building_number):
                evidence_score += 8
                evidence.append("building matched")
            else:
                evidence_score -= 4
                evidence.append("building different")

        # Room-number check
        if room_number:
            csv_room = clean_room_number(resident["room_short"])
            detected_room = clean_room_number(room_number)

            if csv_room == detected_room:
                evidence_score += 12
                evidence.append("room matched")
            else:
                evidence_score -= 6
                evidence.append("room different")

        # Room-letter check
        if room_letter:
            csv_letter = clean_room_letter(resident["room_short"])
            detected_letter = clean_room_letter(room_letter)

            if csv_letter.endswith(detected_letter):
                evidence_score += 4
                evidence.append("room letter matched")
            else:
                evidence_score -= 2
                evidence.append("room letter different")

        # Phone check, when a phone was detected on the label
        if phone_number:
            if phones_match(resident["phone_number"], phone_number):
                evidence_score += 15
                evidence.append("phone matched")
            else:
                evidence_score -= 4
                evidence.append("phone different")

        results.append({
            "index": index,
            "name_score": round(name_score, 1),
            "evidence_score": evidence_score,
            "final_score": round(name_score + evidence_score, 1),
            "evidence": ", ".join(evidence) or "name only",
        })

    if not results:
        print("No reliable resident found for:\n", search_name)
        return None

    ranked = pd.DataFrame(results).sort_values(
        "final_score",
        ascending=False,
    )

    best_result = ranked.iloc[0]
    resident = df.loc[int(best_result["index"])]

    print("Best resident match")
    print("Name:", resident["full_name"])
    print("Legal name:", resident["legal_full_name"])
    print("Student ID:", resident["student_id"])
    print("Room:", resident["room"])
    print("Building:", resident["building"])
    print("Phone:", resident["phone_number"])
    print("Name similarity:", best_result["name_score"])
    print("Additional evidence:", best_result["evidence"])
    print("Final score:", best_result["final_score"])

    # Show alternatives when the top results are very close
    if len(ranked) > 1:
        difference = (
            ranked.iloc[0]["final_score"]
            - ranked.iloc[1]["final_score"]
        )

        if difference < 5:
            print("\nWarning: match is ambiguous.")
            print("Top candidates:")

            candidate_indexes = ranked.head(3)["index"].astype(int)
            print(
                df.loc[
                    candidate_indexes,
                    [
                        "full_name",
                        "legal_full_name",
                        "student_id",
                        "room",
                        "building",
                        "phone_number",
                    ],
                ]
            )

    return resident