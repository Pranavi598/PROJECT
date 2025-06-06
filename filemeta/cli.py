# filemeta/cli.py
import click
import sys
import json # For pretty printing JSON
from datetime import datetime

from .database import init_db, get_db, close_db_engine
from .metadata_manager import add_file_metadata, list_files, get_file_metadata
from sqlalchemy.exc import OperationalError, NoResultFound # Import exceptions

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
        custom_tags[key] = value # Store as string initially, parse_tag_value handles type

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

                # Pretty print inferred tags
                click.echo("  Inferred Tags:")
                click.echo(json.dumps(file_data['Inferred Tags'], indent=2, ensure_ascii=False))

                # Pretty print custom tags
                click.echo("  Custom Tags:")
                if file_data['Custom Tags']:
                    click.echo(json.dumps(file_data['Custom Tags'], indent=2, ensure_ascii=False))
                else:
                    click.echo("    (None)")
            click.echo("-" * 40) # End separator

        except OperationalError as e:
            click.echo(f"Database connection error: {e}. Please ensure the database is running and configured correctly.", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}", err=True)
            sys.exit(1)

if __name__ == '__main__':
    cli()