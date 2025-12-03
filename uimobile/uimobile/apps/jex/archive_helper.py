import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
import io

ARCHIVE_ROOT = os.path.join(os.path.dirname(__file__), "..", "archives")
os.makedirs(ARCHIVE_ROOT, exist_ok=True)

HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/114.0.0.0 Safari/537.36"
}

def archive_page(url, folder_name=None):
    """
    Downloads a webpage and its images into a folder for offline use.
    Saves HTML and images.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

    # Determine folder name
    if not folder_name:
        folder_name = url.replace("://", "_").replace("/", "_")
    archive_path = os.path.join(ARCHIVE_ROOT, folder_name)
    os.makedirs(archive_path, exist_ok=True)

    soup = BeautifulSoup(resp.text, "html.parser")

    # Download images
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if not src:
            continue
        img_url = urljoin(url, src)
        try:
            r = requests.get(img_url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            # Resize for small screen
            im.thumbnail((320,240))
            img_name = os.path.basename(src.split("?")[0])
            if not img_name.lower().endswith(".jpg"):
                img_name += ".jpg"
            im.save(os.path.join(archive_path, img_name), "JPEG")
            # Update tag to local path
            img_tag["src"] = img_name
        except Exception as e:
            print(f"Failed to fetch image {img_url}: {e}")

    # Save HTML
    html_path = os.path.join(archive_path, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Page archived at {archive_path}")
    return archive_path
