# import click
# import sys
# import json
# from datetime import datetime
# import os 
# from contextlib import contextmanager

# # Correct relative imports
# from .database import get_db, init_db, get_user_by_username
# from .api.auth import verify_password # Needed for user authentication
# # No need to import DBFile here if list_files/search_files handle the query internally
# # from .models import File as DBFile # Only needed if querying File model directly in CLI

# from .metadata_manager import (
#     add_file_metadata,
#     list_files, # Assumes it accepts owner_id now
#     get_file_metadata,
#     search_files, # Assumes it accepts owner_id now
#     update_file_tags,
#     delete_file_metadata
# )
# from sqlalchemy.exc import OperationalError, NoResultFound, IntegrityError
# from sqlalchemy.orm import Session # Import Session for type hinting

# # Define a context manager wrapper for get_db specifically for CLI use
# @contextmanager
# def get_db_for_cli():
#     db_session_generator = get_db()
#     db = next(db_session_generator)
#     try:
#         yield db
#     finally:
#         try:
#             # Ensure the generator is fully exhausted to close the session
#             next(db_session_generator, None) # Use None as default to prevent StopIteration
#         except StopIteration:
#             pass # Expected if the generator yields only once
#         except Exception as e:
#             print(f"Warning: Error during get_db_for_cli cleanup: {e}", file=sys.stderr)

# @click.group()
# def cli():
#     """A CLI tool for managing server file metadata."""
#     pass

# @cli.command()
# def init():
#     """Initializes the database by creating all necessary tables."""
#     try:
#         init_db()
#         click.echo("Database initialized successfully.")
#     except OperationalError as e:
#         click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#         sys.exit(1)
#     except Exception as e:
#         click.echo(f"An unexpected error occurred during database initialization: {e}", err=True)
#         sys.exit(1)

# @cli.command()
# @click.argument('filepath', type=click.Path(exists=True, dir_okay=False, readable=True))
# @click.option('--tag', '-t', multiple=True, help='Custom tag in KEY=VALUE format. Can be repeated.')
# @click.option('--user', default="testuser", help="Username of the file owner (default: testuser).")
# @click.option('--password', prompt=True, hide_input=True, help="Password for the specified user.")
# def add(filepath: str, tag: tuple, user: str, password: str):
#     """
#     Adds a new metadata record for an existing file on the server.
#     Custom tags are provided as KEY=VALUE pairs and can be repeated.
#     Requires user authentication to associate the file with an owner.
#     """
#     custom_tags = {}
#     for t in tag:
#         if '=' not in t:
#             click.echo(f"Error: Invalid tag format '{t}'. Must be KEY=VALUE.", err=True)
#             sys.exit(1)
#         key, value = t.split('=', 1)
#         custom_tags[key] = value

#     with get_db_for_cli() as db:
#         try:
#             # Authenticate user to get owner_id
#             db_user = get_user_by_username(db, username=user)
#             if not db_user or not verify_password(password, db_user.hashed_password):
#                 click.echo("Error: Invalid username or password for owner.", err=True)
#                 sys.exit(1)
            
#             owner_id = db_user.id

#             file_record = add_file_metadata(db, filepath, custom_tags, owner_id=owner_id)
#             click.echo(f"Metadata added for file '{file_record.filename}' (ID: {file_record.id}) by user '{db_user.username}'")
#         except FileNotFoundError as e:
#             click.echo(f"Error: {e}", err=True)
#             sys.exit(1)
#         except ValueError as e:
#             click.echo(f"Error: {e}", err=True)
#             sys.exit(1)
#         except IntegrityError as e:
#             click.echo(f"Error: A file with filepath '{filepath}' already exists. {e}", err=True)
#             sys.exit(1)
#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred while adding metadata: {e}", err=True)
#             sys.exit(1)

# @cli.command()
# @click.argument('file_id', type=int)
# def get(file_id: int):
#     """
#     Retrieves and displays the full metadata for a single file by its ID.
#     """
#     with get_db_for_cli() as db:
#         try:
#             file_record = get_file_metadata(db, file_id)

#             click.echo(f"--- Metadata for File ID: {file_record.id} ---")
#             file_data = file_record.to_dict()

#             # --- Using lowercase keys as per models.py to_dict() ---
#             click.echo(f"    Filename: {file_data.get('filename')}")
#             click.echo(f"    Filepath: {file_data.get('filepath')}")
#             click.echo(f"    Owner ID: {file_data.get('owner')}")
#             click.echo(f"    Created By: {file_data.get('created_by')}")
#             click.echo(f"    Created At: {file_data.get('created_at')}")
#             click.echo(f"    Updated At: {file_data.get('updated_at')}")

#             click.echo("    Inferred Tags:")
#             # Note: inferred_tags and tags are different in your to_dict()
#             click.echo(json.dumps(file_data.get('inferred_tags', {}), indent=2, ensure_ascii=False))

#             click.echo("    Custom Tags:")
#             # Custom tags are stored in the 'tags' relationship, not directly in custom_tags column
#             # file_data['tags'] will be a list of dictionaries from Tag.to_dict()
#             # If you want to show them as KEY=VALUE, you need to reformat
#             custom_tags_display = {t['key']: t['value'] for t in file_data.get('tags', [])}
            
#             if custom_tags_display:
#                 click.echo(json.dumps(custom_tags_display, indent=2, ensure_ascii=False))
#             else:
#                 click.echo("      (None)")
#             click.echo("-" * 40)

#         except NoResultFound as e:
#             click.echo(f"Error: {e}", err=True)
#             sys.exit(1)
#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred while retrieving metadata: {e}", err=True)
#             sys.exit(1)


# @cli.command()
# @click.option('--keyword', '-k', multiple=True, help='A keyword to search for. Can be repeated.')
# @click.option('--full', '-f', is_flag=True, help='Display full detailed metadata for each matching file.')
# @click.option("--owner-id", type=int, help="Filter search results by owner ID (Admin function).")
# def search(keyword: tuple, full: bool, owner_id: int):
#     """
#     Finds files whose metadata contains any of the specified keywords.
#     By default, displays a concise list. Use --full for complete details.
#     Admins can use --owner-id to filter results for a specific user.
#     """
#     if not keyword:
#         click.echo("Please provide at least one keyword to search for. Use --keyword <KEYWORD>.")
#         sys.exit(1)

#     search_keywords = list(keyword)

#     with get_db_for_cli() as db:
#         try:
#             files = search_files(db, search_keywords, owner_id=owner_id) # Now passes owner_id

#             if not files:
#                 click.echo(f"No files found matching keywords: {', '.join(search_keywords)}")
#                 return

#             click.echo(f"Found files matching keywords: {', '.join(search_keywords)}")
#             for file_record in files:
#                 file_data = file_record.to_dict()
#                 click.echo("-" * 40)
#                 # --- Using lowercase keys as per models.py to_dict() ---
#                 click.echo(f"    ID: {file_data.get('id')}")
#                 click.echo(f"    Filename: {file_data.get('filename')}")
#                 click.echo(f"    Filepath: {file_data.get('filepath')}")

#                 if full:
#                     click.echo(f"    Owner ID: {file_data.get('owner')}")
#                     click.echo(f"    Created By: {file_data.get('created_by')}")
#                     click.echo(f"    Created At: {file_data.get('created_at')}")
#                     click.echo(f"    Updated At: {file_data.get('updated_at')}")

#                     click.echo("    Inferred Tags:")
#                     click.echo(json.dumps(file_data.get('inferred_tags', {}), indent=2, ensure_ascii=False))

#                     click.echo("    Custom Tags:")
#                     custom_tags_display = {t['key']: t['value'] for t in file_data.get('tags', [])}
#                     if custom_tags_display:
#                         click.echo(json.dumps(custom_tags_display, indent=2, ensure_ascii=False))
#                     else:
#                         click.echo("      (None)")
#             click.echo("-" * 40)

#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred during search: {e}", err=True)
#             sys.exit(1)

# @cli.command()
# @click.argument('file_id', type=int)
# @click.option('--tag', '-t', 'tags_to_add_modify', multiple=True,
#               help='Add or modify a custom tag (e.g., -t project=Beta). Can be used multiple times.')
# @click.option('--remove-tag', '-r', 'tags_to_remove', multiple=True,
#               help='Remove a custom tag by key (e.g., -r confidential). Can be used multiple times.')
# @click.option('--path', '-p', 'new_filepath', type=click.Path(exists=True, dir_okay=False, readable=True),
#               help='Update the file path stored in the database. Provide the new full path.')
# @click.option('--overwrite', is_flag=True,
#               help='If present, all existing custom tags will be deleted BEFORE new tags are added.')
# @click.option("--user", default="testuser", help="Username of the user performing the update (default: testuser).")
# @click.option("--password", prompt=True, hide_input=True, help="Password for the specified user.")
# def update(file_id: int, tags_to_add_modify: tuple, tags_to_remove: tuple, new_filepath: str, overwrite: bool, user: str, password: str):
#     """
#     Updates metadata for a file identified by its ID.
#     Use -t KEY=VALUE to add/modify tags, -r KEY to remove tags.
#     Use -p NEW_PATH to update the file's path.
#     Use --overwrite to clear all existing custom tags before applying new ones.
#     Requires user authentication (must be owner or admin).
#     """
#     if not tags_to_add_modify and not tags_to_remove and not new_filepath and not overwrite:
#         raise click.UsageError(
#             "Please provide at least one option to update "
#             "(e.g., --tag, --remove-tag, --path, or --overwrite)."
#         )

#     if overwrite and tags_to_remove:
#         click.echo("Error: Cannot use --overwrite and --remove-tag together. "
#                     "--overwrite clears all tags before applying new ones.", err=True)
#         sys.exit(1)

#     parsed_add_modify_tags = {}
#     for tag_str in tags_to_add_modify:
#         if '=' not in tag_str:
#             click.echo(f"Error: Invalid tag format '{tag_str}'. Use KEY=VALUE.", err=True)
#             sys.exit(1)
#         key, value = tag_str.split('=', 1)
#         parsed_add_modify_tags[key] = value

#     parsed_remove_tags = list(tags_to_remove) if tags_to_remove else None


#     with get_db_for_cli() as db:
#         try:
#             db_user = get_user_by_username(db, username=user)
#             if not db_user or not verify_password(password, db_user.hashed_password):
#                 click.echo("Error: Invalid username or password.", err=True)
#                 sys.exit(1)

#             file_to_update = get_file_metadata(db, file_id)
#             if not file_to_update:
#                 raise NoResultFound(f"File with ID {file_id} not found.")

#             if db_user.role != 'admin' and file_to_update.owner != db_user.id:
#                 click.echo(f"Error: User '{user}' is not authorized to update file ID {file_id}.", err=True)
#                 sys.exit(1)

#             updated_file = update_file_tags(db, file_id,
#                                             tags_to_add_modify=parsed_add_modify_tags,
#                                             tags_to_remove=parsed_remove_tags,
#                                             new_filepath=new_filepath,
#                                             overwrite_existing=overwrite)
#             click.echo(f"Metadata for file '{updated_file.filename}' (ID: {updated_file.id}) updated successfully.")
#         except NoResultFound as e:
#             click.echo(f"Error: {e}", err=True)
#             sys.exit(1)
#         except ValueError as e:
#             click.echo(f"Error: {e}", err=True)
#             sys.exit(1)
#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred during update: {e}", err=True)
#             sys.exit(1)


# @cli.command()
# @click.argument('file_id', type=int)
# @click.option("--user", default="testuser", help="Username of the user performing the deletion (default: testuser).")
# @click.option("--password", prompt=True, hide_input=True, help="Password for the specified user.")
# def delete(file_id: int, user: str, password: str):
#     """
#     Permanently removes a file's metadata record and its associated tags from the database.
#     This does NOT affect the actual file on the filesystem.
#     Requires user authentication (must be owner or admin).
#     """
#     click.confirm(f"Are you sure you want to permanently delete metadata for file ID {file_id}? This cannot be undone.", abort=True)

#     with get_db_for_cli() as db:
#         try:
#             db_user = get_user_by_username(db, username=user)
#             if not db_user or not verify_password(password, db_user.hashed_password):
#                 click.echo("Error: Invalid username or password.", err=True)
#                 sys.exit(1)

#             file_to_delete = get_file_metadata(db, file_id)
#             if not file_to_delete:
#                 raise NoResultFound(f"File with ID {file_id} not found.")

#             if db_user.role != 'admin' and file_to_delete.owner != db_user.id:
#                 click.echo(f"Error: User '{user}' is not authorized to delete file ID {file_id}.", err=True)
#                 sys.exit(1)

#             delete_file_metadata(db, file_id)
#             click.echo(f"Metadata for file ID {file_id} deleted successfully.")
#         except NoResultFound as e:
#             click.echo(f"Error: {e}", err=True)
#             sys.exit(1)
#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred during deletion: {e}", err=True)
#             sys.exit(1)


# @cli.command(name='list')
# @click.option('--summary', '-s', is_flag=True, default=False, help='Display only file ID, filename, and filepath.') # Added default=False
# @click.option("--owner-id", type=int, help="Filter by owner ID (Admin function).")
# def list_files_cli(summary: bool, owner_id: int):
#     """
#     Displays all file metadata records currently stored in the database.
#     Use --summary for a concise list of just filenames and paths.
#     Admins can use --owner-id to filter results for a specific user.
#     """
#     with get_db_for_cli() as db:
#         try:
#             # Use the updated list_files from metadata_manager that accepts owner_id
#             files = list_files(db, owner_id=owner_id)

#             if not files:
#                 click.echo("No file metadata records found.")
#                 return

#             click.echo("Found files:")
#             for file_record in files:
#                 file_data = file_record.to_dict()
#                 click.echo("-" * 40)
#                 # --- Use lowercase keys from to_dict() ---
#                 click.echo(f"    ID: {file_data.get('id')}")
#                 click.echo(f"    Filename: {file_data.get('filename')}")
#                 click.echo(f"    Filepath: {file_data.get('filepath')}")

#                 # Only print full details if --summary is NOT present
#                 if not summary:
#                     click.echo(f"    Owner ID: {file_data.get('owner')}")
#                     click.echo(f"    Created By: {file_data.get('created_by')}")
#                     click.echo(f"    Created At: {file_data.get('created_at')}")
#                     click.echo(f"    Updated At: {file_data.get('updated_at')}")

#                     click.echo("    Inferred Tags:")
#                     click.echo(json.dumps(file_data.get('inferred_tags', {}), indent=2, ensure_ascii=False))

#                     click.echo("    Custom Tags:")
#                     # Reformat the 'tags' list of dicts into a single dict for display
#                     custom_tags_display = {t['key']: t['value'] for t in file_data.get('tags', [])}
#                     if custom_tags_display:
#                         click.echo(json.dumps(custom_tags_display, indent=2, ensure_ascii=False))
#                     else:
#                         click.echo("      (None)")
#             click.echo("-" * 40)

#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred: {e}", err=True)
#             sys.exit(1)

# @cli.command()
# @click.argument('output_filepath', type=click.Path(dir_okay=False, writable=True))
# def export(output_filepath: str):
#     """
#     Exports all file metadata records to a specified JSON file.
#     """
#     with get_db_for_cli() as db:
#         try:
#             files = list_files(db)
#             if not files:
#                 click.echo("No file metadata records found to export.")
#                 return

#             all_file_data = []
#             for file_record in files:
#                 file_data = file_record.to_dict()
                
#                 # Convert the 'tags' list of dicts into a 'custom_tags' dict for export consistency if desired
#                 # Or keep as 'tags' if that's your export schema
#                 file_data['custom_tags'] = {t['key']: t['value'] for t in file_data.pop('tags', [])}
#                 all_file_data.append(file_data)

#             with open(output_filepath, 'w', encoding='utf-8') as f:
#                 json.dump(all_file_data, f, indent=4, ensure_ascii=False)

#             click.echo(f"Successfully exported {len(files)} file metadata records to '{output_filepath}'.")

#         except OperationalError as e:
#             click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
#             sys.exit(1)
#         except IOError as e:
#             click.echo(f"Error writing to file '{output_filepath}': {e}", err=True)
#             sys.exit(1)
#         except Exception as e:
#             click.echo(f"An unexpected error occurred during export: {e}", err=True)
#             sys.exit(1)

# if __name__ == '__main__':
#     cli()

import click
import sys
import json
from datetime import datetime

from .database import get_db
from .metadata_manager import (
    init_db,
    add_file_metadata,
    list_files,
    get_file_metadata,
    search_files,
    update_file_tags,
    delete_file_metadata
)
from sqlalchemy.exc import OperationalError, NoResultFound, IntegrityError

@click.group()
def cli():
    """A CLI tool for managing server file metadata."""
    pass

@cli.command()
def init():
    """Initializes the database by creating all necessary tables."""
    try:
        init_db()
        click.echo("Database initialized successfully.")
    except OperationalError as e:
        click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during database initialization: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('filepath', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--tag', '-t', multiple=True, help='Custom tag in KEY=VALUE format. Can be repeated.')
def add(filepath, tag):
    """
    Adds a new metadata record for an existing file on the server.
    Custom tags are provided as KEY=VALUE pairs and can be repeated.
    """
    custom_tags = {}
    for t in tag:
        if '=' not in t:
            click.echo(f"Error: Invalid tag format '{t}'. Must be KEY=VALUE.", err=True)
            sys.exit(1)
        key, value = t.split('=', 1)
        custom_tags[key] = value

    with get_db() as db:
        try:
            file_record = add_file_metadata(db, filepath, custom_tags)
            click.echo(f"Metadata added for file '{file_record.filename}' (ID: {file_record.id})")
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred while adding metadata: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.argument('file_id', type=int)
def get(file_id):
    """
    Retrieves and displays the full metadata for a single file by its ID.
    """
    with get_db() as db:
        try:
            file_record = get_file_metadata(db, file_id)

            click.echo(f"--- Metadata for File ID: {file_record.id} ---")
            file_data = file_record.to_dict()

            click.echo(f"   Filename: {file_data['Filename']}")
            click.echo(f"   Filepath: {file_data['Filepath']}")
            click.echo(f"   Owner: {file_data['Owner']}")
            click.echo(f"   Created By: {file_data['Created By']}")
            click.echo(f"   Created At: {file_data['Created At']}")
            click.echo(f"   Updated At: {file_data['Updated At']}")

            click.echo("   Inferred Tags:")
            click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

            click.echo("   Custom Tags:")
            if file_data['Custom Tags']:
                click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
            else:
                click.echo("     (None)")
            click.echo("-" * 40)

        except NoResultFound as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred while retrieving metadata: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.option('--keyword', '-k', multiple=True, help='A keyword to search for. Can be repeated.')
@click.option('--full', '-f', is_flag=True, help='Display full detailed metadata for each matching file.')
def search(keyword, full):
    """
    Finds files whose metadata contains any of the specified keywords.
    By default, displays a concise list. Use --full for complete details.
    """
    if not keyword:
        click.echo("Please provide at least one keyword to search for. Use --keyword <KEYWORD>.")
        sys.exit(1)

    search_keywords = list(keyword)

    with get_db() as db:
        try:
            files = search_files(db, search_keywords)
            if not files:
                click.echo(f"No files found matching keywords: {', '.join(search_keywords)}")
                return

            click.echo(f"Found files matching keywords: {', '.join(search_keywords)}")
            for file_record in files:
                file_data = file_record.to_dict()
                click.echo("-" * 40)
                click.echo(f"   ID: {file_data['ID']}")
                click.echo(f"   Filename: {file_data['Filename']}")
                click.echo(f"   Filepath: {file_data['Filepath']}")

                if full:
                    click.echo(f"   Owner: {file_data['Owner']}")
                    click.echo(f"   Created By: {file_data['Created By']}")
                    click.echo(f"   Created At: {file_data['Created At']}")
                    click.echo(f"   Updated At: {file_data['Updated At']}")

                    click.echo("   Inferred Tags:")
                    click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

                    click.echo("   Custom Tags:")
                    if file_data['Custom Tags']:
                        click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
                    else:
                        click.echo("     (None)")
            click.echo("-" * 40)

        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred during search: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument('file_id', type=int)
@click.option('--tag', '-t', 'tags_to_add_modify', multiple=True,
              help='Add or modify a custom tag (e.g., -t project=Beta). Can be used multiple times.')
@click.option('--remove-tag', '-r', 'tags_to_remove', multiple=True,
              help='Remove a custom tag by key (e.g., -r confidential). Can be used multiple times.')
@click.option('--path', '-p', 'new_filepath', type=click.Path(exists=True, dir_okay=False, readable=True), # Corrected validation here
              help='Update the file path stored in the database. Provide the new full path.')
@click.option('--overwrite', is_flag=True,
              help='If present, all existing custom tags will be deleted BEFORE new tags are added.')
def update(file_id, tags_to_add_modify, tags_to_remove, new_filepath, overwrite):
    """
    Updates metadata for a file identified by its ID.
    Use -t KEY=VALUE to add/modify tags, -r KEY to remove tags.
    Use -p NEW_PATH to update the file's path.
    Use --overwrite to clear all existing custom tags before applying new ones.
    """
    # Corrected validation logic to allow --overwrite by itself
    if not tags_to_add_modify and not tags_to_remove and not new_filepath and not overwrite:
        raise click.UsageError(
            "Please provide at least one option to update "
            "(e.g., --tag, --remove-tag, --path, or --overwrite)."
        )

    if overwrite and tags_to_remove:
        click.echo("Error: Cannot use --overwrite and --remove-tag together. "
                   "--overwrite clears all tags before applying new ones.", err=True)
        sys.exit(1)

    # Process tags to add/modify into a dictionary
    parsed_add_modify_tags = {}
    for tag_str in tags_to_add_modify:
        if '=' not in tag_str:
            click.echo(f"Error: Invalid tag format '{tag_str}'. Use KEY=VALUE.", err=True)
            sys.exit(1)
        key, value = tag_str.split('=', 1)
        parsed_add_modify_tags[key] = value

    # Process tags to remove (ensure it's a list, handle empty case)
    parsed_remove_tags = list(tags_to_remove) if tags_to_remove else None


    with get_db() as db:
        try:
            updated_file = update_file_tags(db, file_id,
                                            tags_to_add_modify=parsed_add_modify_tags,
                                            tags_to_remove=parsed_remove_tags,
                                            new_filepath=new_filepath,
                                            overwrite_existing=overwrite)
            click.echo(f"Metadata for file '{updated_file.filename}' (ID: {updated_file.id}) updated successfully.")
        except NoResultFound as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except ValueError as e: # Catch value errors from metadata_manager (e.g. invalid path for update)
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred during update: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument('file_id', type=int)
def delete(file_id):
    """
    Permanently removes a file's metadata record and its associated tags from the database.
    This does NOT affect the actual file on the filesystem.
    """
    click.confirm(f"Are you sure you want to permanently delete metadata for file ID {file_id}? This cannot be undone.", abort=True)

    with get_db() as db:
        try:
            delete_file_metadata(db, file_id)
            click.echo(f"Metadata for file ID {file_id} deleted successfully.")
        except NoResultFound as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred during deletion: {e}", err=True)
            sys.exit(1)


@cli.command(name='list') # This is the ONLY list command now
@click.option('--summary', '-s', is_flag=True, help='Display only file ID, filename, and filepath.')
def list_files_cli(summary):
    """
    Displays all file metadata records currently stored in the database.
    Use --summary for a concise list of just filenames and paths.
    """
    with get_db() as db:
        try:
            files = list_files(db)
            if not files:
                click.echo("No file metadata records found.")
                return

            click.echo("Found files:")
            for file_record in files:
                file_data = file_record.to_dict()
                click.echo("-" * 40)
                click.echo(f"   ID: {file_data['ID']}")
                click.echo(f"   Filename: {file_data['Filename']}")
                click.echo(f"   Filepath: {file_data['Filepath']}")

                # Only print full details if --summary is NOT present
                if not summary:
                    click.echo(f"   Owner: {file_data['Owner']}")
                    click.echo(f"   Created By: {file_data['Created By']}")
                    click.echo(f"   Created At: {file_data['Created At']}")
                    click.echo(f"   Updated At: {file_data['Updated At']}")

                    click.echo("   Inferred Tags:")
                    click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

                    click.echo("   Custom Tags:")
                    if file_data['Custom Tags']:
                        click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
                    else:
                        click.echo("     (None)")
            click.echo("-" * 40)

        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.argument('output_filepath', type=click.Path(dir_okay=False, writable=True))
def export(output_filepath):
    """
    Exports all file metadata records to a specified JSON file.
    """
    with get_db() as db:
        try:
            files = list_files(db)
            if not files:
                click.echo("No file metadata records found to export.")
                return

            all_file_data = [file_record.to_dict() for file_record in files]

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_file_data, f, indent=4, ensure_ascii=False)

            click.echo(f"Successfully exported {len(files)} file metadata records to '{output_filepath}'.")

        except OperationalError as e:
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except IOError as e:
            click.echo(f"Error writing to file '{output_filepath}': {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred during export: {e}", err=True)
            sys.exit(1)

if __name__ == '__main__':
    cli()