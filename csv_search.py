import pandas as pd
from rapidfuzz import fuzz


def search_csv(search_name):
    df = pd.read_csv(
        "residents_lookup.csv",
        dtype={"student_id": str}
    )

    matches = df.loc[
        df["search_name"] == search_name
    ]

    if len(matches) == 1:
        resident = matches.iloc[0]

        print("Exact resident found!")
        print("Name:", resident["full_name"])
        print("Student ID:", resident["student_id"])
        print("Room:", resident["room"])
        print("Building:", resident["building"])
        return

    if len(matches) > 1:
        print(f"Found {len(matches)} exact matches:")
        print(
            matches[
                ["student_id", "full_name", "room", "building"]
            ]
        )
        return

    # Use rapidfuzz to find the closest match if no exact match is found
    best_score = 0
    best_index = None

    for index, resident_name in df["search_name"].items():
        ratio = fuzz.ratio(resident_name, search_name)

        if ratio > best_score:
            best_score = ratio
            best_index = index

    if best_score >= 85:
        resident = df.loc[best_index]

        print("Possible resident found!")
        print("Name:", resident["full_name"])
        print("Student ID:", resident["student_id"])
        print("Room:", resident["room"])
        print("Building:", resident["building"])
        print("Similarity:", best_score)

    else:
        print("No reliable resident found for:", search_name)
        print("Best similarity score:", best_score)