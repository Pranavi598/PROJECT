# filemeta/utils.py
import os
import pwd
import mimetypes
from datetime import datetime

def infer_metadata(filepath: str) -> dict:
    """
    Infers basic metadata from a given file path.

    Args:
        filepath (str): The absolute or relative path to the file.

    Returns:
        dict: A dictionary containing inferred metadata such as file size,
              last modified time, creation time, owner, and MIME type.
    """
    inferred_data = {}
    try:
        stat_info = os.stat(filepath)

        inferred_data['file_size'] = stat_info.st_size
        inferred_data['last_accessed_at'] = datetime.fromtimestamp(stat_info.st_atime).isoformat()
        inferred_data['last_modified_at'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        # On Unix-like systems, st_ctime is the time of last metadata change (e.g., permissions)
        # On Windows, it's typically the creation time.
        inferred_data['created_at_fs'] = datetime.fromtimestamp(stat_info.st_ctime).isoformat()

        # Try to get owner name (Unix-specific)
        try:
            owner_info = pwd.getpwuid(stat_info.st_uid)
            inferred_data['os_owner'] = owner_info.pw_name
        except KeyError:
            inferred_data['os_owner'] = None # User ID not found
        except Exception as e:
            inferred_data['os_owner'] = f"Error getting owner: {e}"

        # Infer MIME type
        mime_type, _ = mimetypes.guess_type(filepath)
        inferred_data['mime_type'] = mime_type if mime_type else "application/octet-stream"

    except FileNotFoundError:
        # This should ideally be caught before calling this function,
        # but good to have a fallback.
        raise FileNotFoundError(f"File not found: {filepath}")
    except Exception as e:
        # Catch any other potential errors during inference
        inferred_data['error'] = f"Error inferring metadata: {e}"

    return inferred_data

def parse_tag_value(value: str):
    """
    Parses a string value from CLI and attempts to convert it to its
    appropriate Python type (int, float, bool, None) otherwise returns str.
    Returns the value and its type as a string.
    """
    # Try boolean
    if value.lower() == 'true':
        return True, 'bool'
    if value.lower() == 'false':
        return False, 'bool'
    # Try None
    if value.lower() == 'none':
        return None, 'NoneType'
    # Try integer
    try:
        return int(value), 'int'
    except ValueError:
        pass # Not an int
    # Try float
    try:
        return float(value), 'float'
    except ValueError:
        pass # Not a float
    # Default to string
    return value, 'str'