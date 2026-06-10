import argparse

parser = argparse.ArgumentParser(description="Backup Automation")

parser.add_argument(
    "--folder",
    type=str,
    required=True,
    help="Folder to backup"
)

parser.add_argument(
    "--days",
    type=int,
    default=7,
    help="Retention period"
)

args = parser.parse_args()

print(f"Backing up: {args.folder}")
print(f"Retention: {args.days} days")