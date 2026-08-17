from csv_search import search_csv


def test_exact_search_csv():
    # Test with a name that should have an exact match
    print("Testing exact match:")
    exact_tests = [
        "alex clinton",
        "zelandini guterres",
        "sandesha mukundadura",
        "hong chang ma",
        "van nam nguyen",
        "lakshmipriya ramamoorthi",
        "elaina vannieuwenhoven",
        "sjaan toomey jakobs",
        "ta chuang chen",
        "paul gustav lofsberg"
    ]
    for name in exact_tests:
        print(f"Searching for: {name}")
        search_csv(name)
        print("\n")


def test_fuzzy_search_csv():
    # Test with names that should have fuzzy matches
    print("Testing fuzzy match:")
    fuzzy_tests = [
        "apex clinton",  # Alex Clinton
        "zelandini guteres",  # Zelandini Guterres
        "sandesha mukundaduro",  # Sandesha Mukundadura
        "lakshmipriya ramamorthi",  # Lakshmipriya Ramamoorthi
        "elaina vannieuwenhoffen",  # Elaina Vannieuwenhoven
        "hong chang maa",  # Hong Chang Ma
        "van nam nguyem",  # Van Nam Nguyen
        "sjaan toomey jakob",  # Sjaan Toomey-Jakobs
        "paul gustav lofberg"  # Paul Gustav Lofsberg
    ]
    for name in fuzzy_tests:
        print(f"Searching for: {name}")
        search_csv(name)
        print("\n")


def test_ambiguous_search_csv():
    # Test with names that should have ambiguous matches
    print("Testing ambiguous match:")
    ambiguous_tests = [
        "evie",  # Evie Guest and Evie McGinty exist
        "zihan",  # Zihan Liu and Zihan Wang exist
        "jade",  # Jade Askin and Jade Ohlson exist
        "liu",  # Many residents have this surname
        "zhang"  # Many residents have this surname
    ]
    for name in ambiguous_tests:
        print(f"Searching for: {name}")
        search_csv(name)
        print("\n")


if __name__ == "__main__":
    test_exact_search_csv()
    test_fuzzy_search_csv()
    test_ambiguous_search_csv()