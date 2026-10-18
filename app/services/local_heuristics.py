"""Local, deterministic expense categorization rules."""

from __future__ import annotations

from app.config import settings


def classify_description(
    description: str,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
) -> str:
    description_lower = " ".join(description.casefold().split())

    # Each rule lists the workbook-style label first and the starter label
    # second. The first configured label wins, so existing deployments keep
    # their category vocabulary while richer setups get more specific results.
    rules = (
        (
            ("Grocery", "Food"),
            (
                "albert heijn",
                "ah to go",
                "jumbo",
                "lidl",
                "aldi",
                "dirk",
                "plus supermarkt",
                "spar",
                "dekamarkt",
                "grocery",
                "supermarket",
            ),
        ),
        (
            ("Restaurants", "Food"),
            (
                "restaurant",
                "cafe",
                "café",
                "coffee",
                "barista",
                "mcdonald",
                "burger king",
                "kfc",
                "thuisbezorgd",
                "deliveroo",
                "just eat",
                "lunch",
                "dinner",
                "bakery",
                "brood",
            ),
        ),
        (
            ("Alcohol", "Food"),
            ("liquor", "wine store", "slijterij", "gall & gall", "gall gall"),
        ),
        (
            ("Public transport", "Transport"),
            (
                "ov-chipkaart",
                "ns groep",
                "ns.nl",
                " Nederlandse spoorwegen",
                "train",
                "metro",
                "bus",
                "tram",
                "ovpay",
                "connexxion",
                "gvb",
                "arriva",
                "9292",
            ),
        ),
        (
            ("Auto", "Transport"),
            (
                "parking",
                "parkeren",
                "benzine",
                "petrol",
                "fuel",
                "shell",
                "esso",
                "bp ",
                "totalenergies",
                "tango",
                "q-park",
                "anwb",
            ),
        ),
        (("Moto", "Transport"), ("motorcycle", "motor", "scooter")),
        (("Mortgage", "Utilities"), ("hypotheek", "mortgage")),
        (
            ("Health insurance", "Utilities"),
            ("health insurance", "zorgverzekering", "asr ikz zorg", "zorgpremie"),
        ),
        (
            ("Insurance", "Utilities"),
            ("insurance", "verzekering", "verzekerings", "premie"),
        ),
        (
            ("Water", "Utilities"),
            ("waterleiding", "pwn water", "water company", "waterbedrijf"),
        ),
        (
            ("Electricity", "Utilities"),
            (
                "electricity",
                "electriciteit",
                "energieleverancier",
                "vattenfall",
                "eneco",
                "essent",
            ),
        ),
        (
            ("Central heating", "Utilities"),
            ("central heating", " stadsverwarming", "warmte"),
        ),
        (
            ("Internet", "Utilities"),
            ("internet", "broadband", "ziggo", "kpn", "odido", "tele2"),
        ),
        (
            ("Mobile", "Utilities"),
            ("mobile", "mobiel", "telefoon", "phone bill", "sim only"),
        ),
        (
            ("Household", "Shopping"),
            (
                "ikea",
                "action",
                "hema",
                "blokker",
                "household",
                "home goods",
                "woonwinkel",
            ),
        ),
        (
            ("Clothing", "Shopping"),
            (
                "clothing",
                "kleding",
                "fashion",
                "h&m",
                "primark",
                "zalando",
                "c&a",
                "decathlon",
            ),
        ),
        (
            ("Health & Beauty", "Shopping"),
            (
                "holland & barrett",
                "holland and barrett",
                "et os",
                "etos",
                "kruidvat",
                "drogist",
                "beauty",
                "cosmetic",
                "hairdresser",
                "kapper",
            ),
        ),
        (
            ("Health", "Shopping"),
            ("pharmacy", "apotheek", "huisarts", "tandarts", "hospital", "ziekenhuis"),
        ),
        (
            ("Entertainment", "Shopping"),
            (
                "theater",
                "cinema",
                "bioscoop",
                "museum",
                "concert",
                "ticketmaster",
                "tui",
                "netflix",
                "spotify",
            ),
        ),
        (("Subscription", "Utilities"), ("subscription", "abonnement", "membership")),
        (("Sport", "Shopping"), ("sport", "fitness", "gym", "sportschool", "zwembad")),
        (("Toys", "Shopping"), ("toy", "toys", "speelgoed")),
        (("Hobby", "Shopping"), ("hobby", "craft", "game store", "electronics")),
        (("Pocket money", "Other"), ("pocket money", "zakgeld")),
        (("Presents", "Shopping"), ("present", "gift", "cadeau")),
        (("Wellbeing", "Shopping"), ("wellbeing", "wellness", "massage", "spa")),
        (("Credit Card", "Other"), ("credit card", "creditcard", "card repayment")),
        (
            ("Shopping",),
            ("amazon", "shop", "store", "retail", "purchase", "electronics"),
        ),
        (("Transport",), ("uber", "lyft", "taxi", "rail")),
        (("Utilities",), ("gas", "utility", "bill")),
        (("Food",), ("food", "grocer", "grocery", "bakery")),
    )

    allowed = allowed_categories or settings.allowed_categories
    for category_options, keywords in rules:
        if any(keyword in description_lower for keyword in keywords):
            for category in category_options:
                if category in allowed:
                    return category

    return fallback_category or settings.fallback_category
