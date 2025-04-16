# get_hash.py
import hashlib
from pathlib import Path
def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

if __name__ == "__main__":
    model_path = str(Path(__file__).parent.parent / "ml_models/model_weights/gender.pt")  # 修改为实际路径
    print(f"SHA256: {calculate_sha256(model_path)}")
