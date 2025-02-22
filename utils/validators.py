# utils/validators.py
def validate_file_size(file, max_size):
    if file.size > max_size:
        raise ValueError("File size exceeds the allowed limit.")
