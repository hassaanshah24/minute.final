# utils/helpers.py
def generate_unique_id(prefix, department, serial):
    return f"{prefix}/{department}/{serial}"
