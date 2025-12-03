import re

def parse_helpdoc(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    content = {"title": None, "sections": []}
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("TITLE:"):
            content["title"] = line.replace("TITLE:", "").strip()

        elif line.startswith("IMAGE:"):
            if current_section is None:
                current_section = {"header": None, "text": [], "images": [], "table": None}
            current_section["images"].append(line.replace("IMAGE:", "").strip())

        elif line.startswith("SECTION:"):
            if current_section:
                content["sections"].append(current_section)
            current_section = {"header": None, "text": [], "images": [], "table": None}

        elif line.startswith("HEADER:"):
            current_section["header"] = line.replace("HEADER:", "").strip()

        elif line.startswith("TEXT:"):
            current_section["text"] = []

        elif line.startswith("|"):
            # Table line
            if current_section["table"] is None:
                current_section["table"] = []
            columns = [col.strip() for col in line.split("|")[1:-1]]
            current_section["table"].append(columns)

        else:
            # Assume this is part of text content
            if current_section is not None and current_section["text"] is not None:
                current_section["text"].append(line)

    if current_section:
        content["sections"].append(current_section)

    return content
