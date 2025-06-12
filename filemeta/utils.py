# # filemeta/utils.py
# import os
# import mimetypes
# import json
# from datetime import datetime

# def infer_metadata(filepath: str) -> dict:
#     """Infers metadata from a file's path and system stats."""
#     if not os.path.exists(filepath):
#         raise FileNotFoundError(f"File not found: {filepath}")
#     if not os.path.isfile(filepath): # Ensure it's a regular file
#         raise ValueError(f"Path is not a regular file: {filepath}")

#     stat_info = os.stat(filepath)
#     filename = os.path.basename(filepath)
#     name, ext = os.path.splitext(filename)
#     mime_type, _ = mimetypes.guess_type(filepath)

#     inferred = {
#         "filename": filename,
#         "extension": ext.lower() if ext else "",
#         "mime_type": mime_type if mime_type else "application/octet-stream",
#         "file_size": stat_info.st_size, # This is 'file_size'
#         "creation_time_os": datetime.fromtimestamp(stat_info.st_ctime), # Time of metadata change (OS-specific)
#         "last_access_time": datetime.fromtimestamp(stat_info.st_atime),
#         "last_modified_at": datetime.fromtimestamp(stat_info.st_mtime), # This is 'last_modified_at' (as datetime)
#     }
#     return inferred

# def parse_tag_value(value: str):
#     """
#     Attempts to convert a string tag value into a more specific Python type (int, float, bool, list, dict).
#     """
#     value = value.strip()
#     if not value:
#         return value # Return empty string for empty input

#     # Try boolean
#     if value.lower() == 'true':
#         return True
#     if value.lower() == 'false':
#         return False

#     # Try integer
#     try:
#         return int(value)
#     except ValueError:
#         pass

#     # Try float
#     try:
#         return float(value)
#     except ValueError:
#         pass

#     # Try JSON (for list or dict)
#     if (value.startswith('[') and value.endswith(']')) or \
#        (value.startswith('{') and value.endswith('}')):
#         try:
#             return json.loads(value)
#         except json.JSONDecodeError:
#             pass # Not a valid JSON string, treat as string

#     # Default to string
#     return value
# filemeta/utils.py
# filemeta/utils.py
import os
import re
import pwd
import mimetypes
from datetime import datetime, timezone, timedelta

def infer_metadata(filepath: str) -> dict:
    """
    Infers basic metadata from a given file path.
    """
    inferred_data = {}
    try:
        stat_info = os.stat(filepath)

        inferred_data['file_size'] = stat_info.st_size
        # Store these in ISO format to preserve timezone info if available, or assume UTC for consistency
        inferred_data['last_accessed_at'] = datetime.fromtimestamp(stat_info.st_atime, tz=timezone.utc).isoformat()
        inferred_data['last_modified_at'] = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat()
        inferred_data['created_at_fs'] = datetime.fromtimestamp(stat_info.st_ctime, tz=timezone.utc).isoformat()

        try:
            owner_info = pwd.getpwuid(stat_info.st_uid)
            inferred_data['os_owner'] = owner_info.pw_name
        except KeyError:
            inferred_data['os_owner'] = None
        except Exception as e:
            inferred_data['os_owner'] = f"Error getting owner: {e}"

        mime_type, _ = mimetypes.guess_type(filepath)
        inferred_data['mime_type'] = mime_type if mime_type else "application/octet-stream"

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except Exception as e:
        inferred_data['error'] = f"Error inferring metadata: {e}"

    return inferred_data

def parse_tag_value(value: str):
    """
    Parses a string value from CLI and attempts to convert it to its
    appropriate Python type (int, float, bool, None) otherwise returns str.
    Returns the value and its type as a string.
    """
    if value.lower() == 'true':
        return True, 'bool'
    if value.lower() == 'false':
        return False, 'bool'
    if value.lower() == 'none':
        return None, 'NoneType'
    try:
        return int(value), 'int'
    except ValueError:
        pass
    try:
        return float(value), 'float'
    except ValueError:
        pass
    return value, 'str'

def convert_human_readable_to_bytes(size_str: str) -> int:
    """
    Converts a human-readable file size string (e.g., "10KB", "1.5GB", "500B")
    into an integer representing the size in bytes.
    """
    size_str = size_str.strip().upper()
    
    match = re.match(r'^(\d+(\.\d+)?)\s*([KMGTPE]?B)?$', size_str)
    
    if not match:
        raise ValueError(f"Invalid size format: '{size_str}'. Expected formats like '100B', '10KB', '1.5MB', '2GB'.")

    value = float(match.group(1))
    unit = match.group(3)

    if unit is None or unit == 'B':
        return int(value)
    elif unit == 'KB':
        return int(value * (1024**1))
    elif unit == 'MB':
        return int(value * (1024**2))
    elif unit == 'GB':
        return int(value * (1024**3))
    elif unit == 'TB':
            return int(value * (1024**4))
    elif unit == 'PB':
            return int(value * (1024**5))
    elif unit == 'EB':
            return int(value * (1024**6))
    else:
            raise ValueError(f"Unknown unit: '{unit}' in '{size_str}'.")

def parse_date_string(date_str: str) -> datetime:
    """
    Parses a date string (e.g., '2024-01-01', '2024-06-11 10:00:00') into a datetime object.
    Attempts various common formats. Assumes UTC if no timezone info.
    """
    formats_to_try = [
        "%Y-%m-%dT%H:%M:%S.%f%z", # ISO format with microseconds and timezone
        "%Y-%m-%dT%H:%M:%S%z",   # ISO format with seconds and timezone
        "%Y-%m-%d %H:%M:%S%z",   # Space instead of T, with timezone
        "%Y-%m-%d %H:%M:%S",     # YYYY-MM-DD HH:MM:SS
        "%Y-%m-%d %H:%M",        # YYYY-MM-DD HH:MM
        "%Y-%m-%d"               # YYYY-MM-DD
    ]
    for fmt in formats_to_try:
        try:
            # If format includes timezone, fromisoformat handles it.
            # Otherwise, localize to UTC
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    # Try fromisoformat directly as a fallback for complex ISO strings
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    raise ValueError(f"Could not parse date string: '{date_str}'. Expected formats like 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.")

