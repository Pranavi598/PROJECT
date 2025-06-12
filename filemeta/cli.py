


#     cli()
import click
import sys
import json
from datetime import datetime, timedelta
import logging # Import the logging module

# Configure logging to suppress SQLAlchemy INFO messages
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from filemeta.database import get_db
from filemeta.metadata_manager import (
    init_db,
    add_file_metadata,
    list_files,
    get_file_metadata,
    search_files_by_criteria, # Use the new comprehensive search function
    update_file_tags,
    delete_file_metadata,
    rename_file_entry,
    list_and_search_tags,
    validate_file_metadata
)
from filemeta.utils import parse_tag_value, convert_human_readable_to_bytes, parse_date_string
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
@click.option('-k', '--keywords', multiple=True, help='Keywords to search for in file metadata (filename, path, owner, tags).')
@click.option('--size-gt', type=str, help='Search for files larger than the specified size (e.g., "10MB", "1GB").')
@click.option('--size-lt', type=str, help='Search for files smaller than the specified size (e.g., "100KB", "1GB").')
@click.option('--size-between', nargs=2, type=str, help='Search for files within a size range (e.g., "100KB 1MB"). Requires two values.')
# --- NEW: Date/Time Search Options ---
@click.option('--created-after', type=str, help="Search for files created after this date/time (e.g., '2024-01-01' or '2024-06-11 10:00:00').")
@click.option('--created-before', type=str, help="Search for files created before this date/time.")
@click.option('--modified-after', type=str, help="Search for files modified after this date/time.")
@click.option('--modified-before', type=str, help="Search for files modified before this date/time.")
@click.option('--accessed-after', type=str, help="Search for files last accessed after this date/time.")
@click.option('--accessed-before', type=str, help="Search for files last accessed before this date/time.")
@click.option('--created-between', nargs=2, type=str, help="Search for files created within this date/time range (e.g., '2024-01-01' '2024-03-31').")
@click.option('--modified-between', nargs=2, type=str, help="Search for files modified within this date/time range.")
@click.option('--accessed-between', nargs=2, type=str, help="Search for files last accessed within this date/time range.")
# --- END NEW DATE/TIME OPTIONS ---
@click.option('--full', '-f', is_flag=True, help='Display full detailed metadata for each matching file.')
def search(
    keywords, size_gt, size_lt, size_between,
    created_after, created_before, modified_after, modified_before,
    accessed_after, accessed_before,
    created_between, modified_between, accessed_between,
    full # Added full parameter to the function signature
):
    """
    Search for file metadata based on keywords, size, and date/time ranges.
    Date formats: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.
    """
    # Check if any search criterion is provided
    if not any([
        keywords, size_gt, size_lt, size_between,
        created_after, created_before, modified_after, modified_before,
        accessed_after, accessed_before, created_between, modified_between, accessed_between
    ]):
        click.echo("Please provide at least one search criterion (keywords, size, or date range).")
        sys.exit(1)

    # Parse size parameters
    min_size_bytes = None
    max_size_bytes = None
    try:
        if size_gt:
            min_size_bytes = convert_human_readable_to_bytes(size_gt)
        if size_lt:
            max_size_bytes = convert_human_readable_to_bytes(size_lt)
        if size_between:
            if len(size_between) != 2:
                click.echo("Error: --size-between requires exactly two values (start and end).", err=True)
                sys.exit(1)
            min_size_bytes = convert_human_readable_to_bytes(size_between[0])
            max_size_bytes = convert_human_readable_to_bytes(size_between[1])
    except ValueError as e:
        click.echo(f"Error parsing size value: {e}", err=True)
        sys.exit(1)

    # Parse date parameters
    parsed_created_after = None
    parsed_created_before = None
    parsed_modified_after = None
    parsed_modified_before = None
    parsed_accessed_after = None
    parsed_accessed_before = None

    try:
        if created_after:
            parsed_created_after = parse_date_string(created_after)
        if created_before:
            parsed_created_before = parse_date_string(created_before)
        if created_between:
            if len(created_between) != 2:
                click.echo("Error: --created-between requires exactly two values (start and end).", err=True)
                sys.exit(1)
            parsed_created_after = parse_date_string(created_between[0])
            parsed_created_before = parse_date_string(created_between[1])

        if modified_after:
            parsed_modified_after = parse_date_string(modified_after)
        if modified_before:
            parsed_modified_before = parse_date_string(modified_before)
        if modified_between:
            if len(modified_between) != 2:
                click.echo("Error: --modified-between requires exactly two values (start and end).", err=True)
                sys.exit(1)
            parsed_modified_after = parse_date_string(modified_between[0])
            parsed_modified_before = parse_date_string(modified_between[1])

        if accessed_after:
            parsed_accessed_after = parse_date_string(accessed_after)
        if accessed_before:
            parsed_accessed_before = parse_date_string(accessed_before)
        if accessed_between:
            if len(accessed_between) != 2:
                click.echo("Error: --accessed-between requires exactly two values (start and end).", err=True)
                sys.exit(1)
            parsed_accessed_after = parse_date_string(accessed_between[0])
            parsed_accessed_before = parse_date_string(accessed_between[1])

    except ValueError as e:
        click.echo(f"Error parsing date value: {e}", err=True)
        sys.exit(1)

    with get_db() as db:
        try:
            # Call the comprehensive search function from metadata_manager
            files = search_files_by_criteria(
                db=db,
                keywords=list(keywords) if keywords else None,
                min_size_bytes=min_size_bytes,
                max_size_bytes=max_size_bytes,
                created_after=parsed_created_after,
                created_before=parsed_created_before,
                modified_after=parsed_modified_after,
                modified_before=parsed_modified_before,
                accessed_after=parsed_accessed_after,
                accessed_before=parsed_accessed_before
            )

            if not files:
                click.echo("No files found matching the criteria.")
                return

            click.echo("Found files:")
            for file_record in files:
                file_data = file_record.to_dict()
                click.echo("-" * 40)
                click.echo(f"   ID: {file_data.get('ID')}")
                click.echo(f"   Filename: {file_data.get('Filename')}")
                click.echo(f"   Filepath: {file_data.get('Filepath')}")

                if full: # Conditional output based on --full flag
                    click.echo(f"   Owner: {file_data.get('Owner')}")
                    click.echo(f"   Created By: {file_data.get('Created By')}")
                    click.echo(f"   Created At (DB): {file_data.get('Created At')}")
                    click.echo(f"   Updated At (DB): {file_data.get('Updated At')}")
                    
                    inferred_tags = file_data.get('Inferred Tags', {})
                    click.echo(f"   Inferred Tags (Size): {inferred_tags.get('file_size')} bytes")
                    click.echo(f"   Inferred Tags (Last Accessed FS): {inferred_tags.get('last_accessed_at')}")
                    click.echo(f"   Inferred Tags (Last Modified FS): {inferred_tags.get('last_modified_at')}")
                    click.echo(f"   Inferred Tags (Created FS): {inferred_tags.get('created_at_fs')}")
                    
                    click.echo("   Custom Tags:")
                    if file_data.get('Custom Tags'):
                        click.echo(json.dumps(file_data.get('Custom Tags'), indent=2, ensure_ascii=False))
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
@click.option('--path', '-p', 'new_filepath', type=click.Path(exists=True, dir_okay=False, readable=True),
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
    if not tags_to_add_modify and not tags_to_remove and not new_filepath and not overwrite:
        raise click.UsageError(
            "Please provide at least one option to update "
            "(e.g., --tag, --remove-tag, --path, or --overwrite)."
        )

    if overwrite and tags_to_remove:
        click.echo("Error: Cannot use --overwrite and --remove-tag together. "
                    "--overwrite clears all tags before applying new ones.", err=True)
        sys.exit(1)

    parsed_add_modify_tags = {}
    for tag_str in tags_to_add_modify:
        if '=' not in tag_str:
            click.echo(f"Error: Invalid tag format '{tag_str}'. Use KEY=VALUE.", err=True)
            sys.exit(1)
        key, value = tag_str.split('=', 1)
        parsed_add_modify_tags[key] = value

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


@cli.command(name='list')
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
@cli.command()
@click.argument('file_id', type=int)
@click.argument('new_name')
def rename(file_id, new_name):
    """
    Renames a file on disk and updates its metadata in the database.
    Args:
        file_id (int): The ID of the file metadata record to rename.
        new_name (str): The new filename (e.g., "document_v2.pdf").
                        This should be just the name, not a full path.
    """
    try:
        with get_db() as db:
            updated_file = rename_file_entry(db, file_id, new_name)
            click.echo(f"File ID {file_id} successfully renamed.")
            click.echo("Updated metadata:")
            click.echo(json.dumps(updated_file.to_dict(), indent=2))
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
    except NoResultFound as e:
        click.echo(f"Error: {e}", err=True)
    except PermissionError as e:
        click.echo(f"Permission denied: {e}", err=True)
    except OSError as e: # Catch other OS-level errors like invalid filename
        click.echo(f"File system error during rename: {e}", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
@cli.group()
def tags():
    """Manage and query custom tags."""
    pass

@tags.command(name='list')
@click.option('--unique', is_flag=True, help='List only unique tag keys or unique key-value pairs.')
@click.option('--sort', type=click.Choice(['key', 'value'], case_sensitive=False), help='Sort results by tag key or tag value.')
@click.option('--order', type=click.Choice(['asc', 'desc'], case_sensitive=False), default='asc', help='Order of sorting (asc/desc). Defaults to ascending.')
@click.option('--limit', type=int, help='Limit the number of results returned.')
@click.option('--offset', type=int, default=0, help='Offset the results by this number.')
@click.option('-s', '--search-keywords', multiple=True, help='Search for tags containing these keywords in key or value.')
def list_tags_command(unique, sort, order, limit, offset, search_keywords):
    """
    List custom tags with various filtering and sorting options.
    Use --unique to get unique tag keys or unique key-value pairs.
    """
    try:
        with get_db() as db:
            if unique:
                # For unique, we might simplify what's returned to just the distinct keys or key-value tuples
                results = list_and_search_tags(db, unique=unique, sort_by=sort, sort_order=order, limit=limit, offset=offset, keywords=list(search_keywords))
                if not results:
                    click.echo("No unique tags found matching criteria.")
                else:
                    click.echo("Unique Tags:")
                    for r in results:
                        if isinstance(r, tuple): # If unique key-value pairs
                            click.echo(f"  {r[0]}: {r[1]}")
                        else: # If unique keys
                            click.echo(f"  {r}")
            else:
                # For non-unique, list full tag objects or their dict representation
                tag_records = list_and_search_tags(db, unique=unique, sort_by=sort, sort_order=order, limit=limit, offset=offset, keywords=list(search_keywords))
                if not tag_records:
                    click.echo("No tags found matching criteria.")
                else:
                    click.echo("Tags:")
                    for tag in tag_records:
                        click.echo(f"  ID: {tag.id}, File ID: {tag.file_id}, Key: {tag.key}, Value: {tag.get_typed_value()} ({tag.value_type})")

    except Exception as e:
        click.echo(f"Error listing tags: {e}", err=True)
@cli.command()
@click.option('--id', 'file_id', type=int, help='Validate a specific file by its database ID.')
@click.option('--filename', help='Validate files with a specific filename.')
@click.option('--filepath', help='Validate files with a specific filepath.')
@click.option('--tag', 'tag_check', type=str, help='Validate files that have a specific tag (e.g., "project=backend" or just "project").')
@click.option('--all', is_flag=True, help='Validate all records in the database. (Performs file existence check for all entries).')
def validate(file_id, filename, filepath, tag_check, all):
    """
    Validates file metadata against actual file system existence and specific tag presence.
    """
    if not (file_id or filename or filepath or tag_check or all):
        click.echo("Please provide at least one validation criterion (--id, --filename, --filepath, --tag, or --all).")
        return

    try:
        with get_db() as db:
            if all:
                click.echo("Validating all file metadata records...")
                validation_results = validate_file_metadata(db, check_all=True)
            else:
                # Build a dictionary of criteria for specific validation
                criteria = {}
                if file_id:
                    criteria['id'] = file_id
                if filename:
                    criteria['filename'] = filename
                if filepath:
                    criteria['filepath'] = filepath
                
                tag_key = None
                tag_value = None
                if tag_check:
                    if '=' in tag_check:
                        tag_key, tag_value = tag_check.split('=', 1)
                    else:
                        tag_key = tag_check

                validation_results = validate_file_metadata(db, criteria=criteria, tag_key=tag_key, tag_value=tag_value)

            if not validation_results:
                click.echo("No records found matching validation criteria, or no issues found.")
                return

            click.echo("\n--- Validation Results ---")
            for result in validation_results:
                click.echo(f"File ID: {result['id']}, Path: {result['filepath']}")
                if result['disk_exists'] is False:
                    click.echo("  Status: MISSING ON DISK")
                if result['tag_status']:
                    click.echo(f"  Tag Check: {result['tag_status']}")
                click.echo("-" * 30)

    except Exception as e:
        click.echo(f"Error during validation: {e}", err=True)

if __name__ == '__main__':
    cli()
