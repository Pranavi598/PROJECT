

# filemeta/cli.py
import click
import sys
import json
from datetime import datetime

from .database import init_db, get_db, close_db_engine
from .metadata_manager import add_file_metadata, list_files, get_file_metadata, search_files, update_file_tags # Ensure all functions are imported
from sqlalchemy.exc import OperationalError, NoResultFound

@click.group()
def cli():
    """A CLI tool for managing server file metadata."""
    pass

@cli.command()
def init():
    """Initializes the database by creating all necessary tables."""
    init_db()

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
            click.echo(f"Database connection error: {e}. Please ensure the database is running and configured correctly.", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.option('--keyword', '-k', multiple=True, help='A keyword to search for. Can be repeated.')
def search(keyword):
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

            click.echo(f"Found files matching keywords: {', '.join(search_keywords)}:") # Adjusted message
            for file_record in files:
                # --- MODIFICATION START ---
                # Instead of printing all metadata, just print the filename
                click.echo(f"- {file_record.filename}")
                # --- MODIFICATION END ---

        except OperationalError as e:
            click.echo(f"Database connection error: {e}. Please ensure the database is running and configured correctly.", err=True)
            sys.exit(1)
        except Exception as e:
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
        except NoResultFound as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except OperationalError as e:
            click.echo(f"Database connection error: {e}. Please ensure the database is running and configured correctly.", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred during update: {e}", err=True)
            sys.exit(1)

@cli.command(name='list')
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
                click.echo(f"   ID: {file_data['ID']}")
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

        except OperationalError as e:
            click.echo(f"Database connection error: {e}. Please ensure the database is running and configured correctly.", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}", err=True)
            sys.exit(1)

if __name__ == '__main__':
    cli()
