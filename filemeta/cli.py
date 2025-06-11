# filemeta/cli.py - COMPLETE UPDATED FILE WITH ENHANCED ERROR HANDLING AND 'GET' COMMAND
import click
import sys
import json
from datetime import datetime

from .database import init_db, get_db, close_db_engine
from .metadata_manager import add_file_metadata, list_files, get_file_metadata, search_files, update_file_tags, delete_file_metadata
from sqlalchemy.exc import OperationalError, NoResultFound, IntegrityError # Added IntegrityError for specific catch

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
    except OperationalError as e: # Specific database connection error
        click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
        sys.exit(1)
    except Exception as e: # Catch-all for other unexpected errors
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
        except ValueError as e: # For duplicate filepath from metadata_manager
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e: # Specific database connection error
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e: # Catch-all for other unexpected errors
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

            click.echo(f"  Filename: {file_data['Filename']}")
            click.echo(f"  Filepath: {file_data['Filepath']}")
            click.echo(f"  Owner: {file_data['Owner']}")
            click.echo(f"  Created By: {file_data['Created By']}")
            click.echo(f"  Created At: {file_data['Created At']}")
            click.echo(f"  Updated At: {file_data['Updated At']}")

            click.echo("  Inferred Tags:")
            click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

            click.echo("  Custom Tags:")
            if file_data['Custom Tags']:
                click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
            else:
                click.echo("    (None)")
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
                click.echo(f"  ID: {file_data['ID']}")
                click.echo(f"  Filename: {file_data['Filename']}")
                click.echo(f"  Filepath: {file_data['Filepath']}")

                if full:
                    click.echo(f"  Owner: {file_data['Owner']}")
                    click.echo(f"  Created By: {file_data['Created By']}")
                    click.echo(f"  Created At: {file_data['Created At']}")
                    click.echo(f"  Updated At: {file_data['Updated At']}")

                    click.echo("  Inferred Tags:")
                    click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

                    click.echo("  Custom Tags:")
                    if file_data['Custom Tags']:
                        click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
                    else:
                        click.echo("    (None)")
            click.echo("-" * 40)

        except OperationalError as e: # Specific database connection error
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e: # Catch-all for other unexpected errors
            click.echo(f"An unexpected error occurred during search: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument('file_id', type=int)
@click.option('--tag', '-t', multiple=True, help='New or updated custom tag in KEY=VALUE format. Can be repeated.')
@click.option('--overwrite', is_flag=True, help='If present, all existing custom tags will be deleted before new tags are added.')
def update(file_id, tag, overwrite):
    """
    Modifies or adds custom tags for a specific file identified by its FILE_ID.
    """
    if not tag and not overwrite:
        click.echo("Error: Please provide at least one --tag to update/add, or use --overwrite to clear all custom tags.", err=True)
        sys.exit(1)
    if not tag and overwrite:
        click.confirm(f"Are you sure you want to delete ALL custom tags for file ID {file_id}?", abort=True)

    new_tags = {}
    for t in tag:
        if '=' not in t:
            click.echo(f"Error: Invalid tag format '{t}'. Must be KEY=VALUE.", err=True)
            sys.exit(1)
        key, value = t.split('=', 1)
        new_tags[key] = value

    with get_db() as db:
        try:
            updated_file = update_file_tags(db, file_id, new_tags, overwrite)
            click.echo(f"Tags updated for file '{updated_file.filename}' (ID: {updated_file.id})")
        except NoResultFound as e: # Specific NoResultFound from metadata_manager
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e: # Specific database connection error
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e: # Catch-all for other unexpected errors
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
        except NoResultFound as e: # Specific NoResultFound from metadata_manager
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e: # Specific database connection error
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e: # Catch-all for other unexpected errors
            click.echo(f"An unexpected error occurred during deletion: {e}", err=True)
            sys.exit(1)


@cli.command(name='list') # Renamed to avoid conflict with built-in list
def list_files_cli():
    """
    Displays all file metadata records currently stored in the database,
    including automatically inferred details and user-defined custom tags.
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
                click.echo(f"  ID: {file_data['ID']}")
                click.echo(f"  Filename: {file_data['Filename']}")
                click.echo(f"  Filepath: {file_data['Filepath']}")
                click.echo(f"  Owner: {file_data['Owner']}")
                click.echo(f"  Created By: {file_data['Created By']}")
                click.echo(f"  Created At: {file_data['Created At']}")
                click.echo(f"  Updated At: {file_data['Updated At']}")

                click.echo("  Inferred Tags:")
                click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

                click.echo("  Custom Tags:")
                if file_data['Custom Tags']:
                    click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
                else:
                    click.echo("    (None)")
            click.echo("-" * 40)

        except OperationalError as e: # Specific database connection error
            click.echo(f"Database connection error: {e}\nPlease ensure the database server is running and accessible (check credentials, host, port, and firewall).", err=True)
            sys.exit(1)
        except Exception as e: # Catch-all for other unexpected errors
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

            # Convert list of File objects to a list of dictionaries
            # using the .to_dict() method available on File objects
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