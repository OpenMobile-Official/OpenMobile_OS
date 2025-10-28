import os

def list_all_files(start_path='.'):
    print(f"Listing all files in: {os.path.abspath(start_path)}\n")
    for root, dirs, files in os.walk(start_path):
        for file in files:
            full_path = os.path.join(root, file)
            print(full_path)

if __name__ == "__main__":
    list_all_files()
