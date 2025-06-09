import json
import random
import string


def generate_random_string(length=10):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def expand_list(original_list, min_length=50):
    if isinstance(original_list, list):
        current_length = len(original_list)
        if current_length < min_length:
            if all(isinstance(i, str) for i in original_list):
                # Expand list of strings
                for _ in range(min_length - current_length):
                    original_list.append(generate_random_string())
            elif all(isinstance(i, dict) for i in original_list):
                # Expand list of dicts by duplicating last element
                if current_length > 0:
                    item_to_duplicate = original_list[-1]
                    for _ in range(min_length - current_length):
                        original_list.append(item_to_duplicate.copy())
            elif all(isinstance(i, list) for i in original_list):
                # Expand list of lists by duplicating last element
                if current_length > 0:
                    item_to_duplicate = original_list[-1]
                    for _ in range(min_length - current_length):
                        original_list.append(item_to_duplicate.copy())


def traverse_and_expand(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "options" and isinstance(value, list):
                expand_list(value)
            elif isinstance(value, (dict, list)):
                traverse_and_expand(value)
    elif isinstance(data, list):
        for item in data:
            traverse_and_expand(item)


def main():
    file_path = "audio_ficition/fantasy/config.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        # Attempt to fix common JSON issues like trailing commas
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.strip()
        # This is a very basic fix, more robust solutions might be needed
        if content.endswith(","):
            content = content[:-1]
        try:
            config_data = json.loads(content)
        except json.JSONDecodeError as e2:
            print(f"Could not fix JSON, still getting error: {e2}")
            return

    traverse_and_expand(config_data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
