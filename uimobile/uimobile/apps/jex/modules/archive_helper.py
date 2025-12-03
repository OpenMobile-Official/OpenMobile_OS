import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "..", "archives")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def save_page(url, folder_name=None):
    """
    Saves the HTML and images of a web page locally.

    :param url: URL of the page to archive
    :param folder_name: Optional folder name. If None, derived from URL
    :return: Path to the saved folder
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"[Archive] Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Folder name
    if not folder_name:
        parsed = urlparse(url)
        folder_name = parsed.netloc.replace(".", "_")
    save_path = os.path.join(ARCHIVE_DIR, folder_name)
    os.makedirs(save_path, exist_ok=True)

    # Save HTML
    html_file = os.path.join(save_path, "index.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(str(soup))

    # Download images
    img_tags = soup.find_all("img")
    for i, img in enumerate(img_tags):
        img_url = img.get("src")
        if not img_url:
            continue
        # Make relative URLs absolute
        img_url = requests.compat.urljoin(url, img_url)
        try:
            img_data = requests.get(img_url).content
            ext = os.path.splitext(img_url)[-1].split("?")[0] or ".jpg"
            img_file = os.path.join(save_path, f"img_{i}{ext}")
            with open(img_file, "wb") as f:
                f.write(img_data)
        except Exception as e:
            print(f"[Archive] Failed to save image {img_url}: {e}")

    print(f"[Archive] Saved {url} to {save_path}")
    return save_path
