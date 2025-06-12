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