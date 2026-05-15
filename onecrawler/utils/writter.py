import json


def save_json(data: dict, filename: str) -> None:
    """Saves a dictionary to a JSON file with proper encoding and indentation.

    Args:
        data (dict): The dictionary to save.
        filename (str): The path to the output file.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
