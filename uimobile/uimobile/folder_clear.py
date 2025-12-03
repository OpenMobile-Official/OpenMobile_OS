import os
import json

def main():
    # Detect script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config", "folders.json")

    # Load JSON
    with open(config_path, "r", encoding="utf-8") as f:
        folders = json.load(f)

    # Filter out empty folders
    cleaned_folders = [folder for folder in folders if folder.get("apps")]

    # Save back to file
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_folders, f, indent=4)

    print(f"Cleaned {config_path}. Removed empty folders.")

if __name__ == "__main__":
    main()
