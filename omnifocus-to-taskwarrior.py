#!/usr/bin/env python

# Keys are OmniFocus column names in the exported CSV file, values are the
# corresponding TaskWarrior attribute names.
FIELD_MAP = {
  "Task ID": "project-tree-id",
  "Type": None, # Not currently used
  "Name": "description",
  "Status": None, # Not currently used, calculated from other values
  "Project": "project",
  "Context": "tags",
  "Start Date": "scheduled",
  "Due Date": "due",
  "Completion Date": "end",
  "Duration": None, # Not currently used
  "Flagged": "priority",
  "Notes": "notes",
}

VERSION="1.0"
DEFAULT_INPUT_FILEPATH = "omnifocus.csv"
DEFAULT_OUTPUT_FILEPATH = "taskwarrior.json"

NOTES_NEWLINE="###NEWLINE###"

import optparse
import csv
import json
import time
import uuid
import pendulum
import re
import copy
from datetime import datetime

from pprint import pprint

parser = optparse.OptionParser(
  usage='%prog [options]',
  version=VERSION,
  epilog="""
OmniFocus provides export to CSV format, this script performs a conversion
to the JSON format used by TaskWarrior for imports, making some
case-specific format conversions as necessary.

Since field changes between various software versions are possible, a
mapping is present at the top of this script that can be edited to perform
the proper field conversions -- the script uses this map to convert any CSV
column names into the appropriate TaskWarrior field values.
"""
)
parser.add_option('-i', '--input',
  dest="input_filename",
  default=DEFAULT_INPUT_FILEPATH,
  help="Filepath to OmniFocus data as JSON, default: %s" % DEFAULT_INPUT_FILEPATH,
)
parser.add_option('-o', '--output',
  dest="output_filename",
  default=DEFAULT_OUTPUT_FILEPATH,
  help="Filepath to output JSON for TaskWarrior, default: %s." % DEFAULT_OUTPUT_FILEPATH,
)
parser.add_option('-a', '--append',
  dest="append_to_file",
  default=False,
  action="store_true",
  help="Append to existing file, default is to overwrite",
)
parser.add_option('-v', '--verbose',
  dest="verbose",
  default=False,
  action="store_true",
  help="Output conversion logging.",
)
parser.add_option('--date-only',
  dest="date_only",
  default=False,
  action="store_true",
  help="Convert non-system dates to use no time, default is False",
)
parser.add_option('--start-date-is-wait',
  dest="start_date_is_wait",
  default=False,
  action="store_true",
  help="Map Start Date to 'wait' attribute (default is 'scheduled' attribute)",
)
parser.add_option('--context-as-tag',
  dest="context_as_tag",
  default=False,
  action="store_true",
  help="Convert contexts to tags",
)
parser.add_option('--flagged-to-high-priority',
  dest="flagged_to_high_priority",
  default=False,
  action="store_true",
  help="Convert flagged actions to high priority tasks, default is False",
)
parser.add_option('--flagged-as-tag',
  dest="flagged_as_tag",
  default=False,
  action="store_true",
  help="Convert flagged actions to a 'flagged' tag",
)
parser.add_option('--standardize-project-names',
  dest="standardize_project_names",
  default=False,
  action="store_true",
  help="Camel case, remove all non-alphanumeric characters and whitespace from project names",
)
parser.add_option('--export-notes',
  dest="export_notes",
  default=False,
  action="store_true",
  help="Export project/task notes to a 'notes' UDA, create 'Notes' tasks for project notes.",
)
options, remainder = parser.parse_args()

output_filemode = "w+" if options.append_to_file else "w"

def current_time():
  return pendulum.now().in_tz('Etc/UTC')

def current_time_iso():
  return to_iso_string(current_time())

def to_iso_string(utc_datetime, date_only = False):
  format_string = "YYYYMMDDTHHmmss\Z"
  if date_only:
    local_datetime = utc_datetime.in_tz('local')
    local_datetime_no_time = pendulum.datetime(local_datetime.year, local_datetime.month, local_datetime.day, tz='local')
    utc_datetime = local_datetime_no_time.in_tz('Etc/UTC')
  return utc_datetime.format(format_string)

def convert_column_value(colname, val):
  # Date conversion.
  if colname in ["scheduled", "due", "end"]:
    format_string = "YYYY-MM-DD HH:mm:ss"
    if val:
      utc_datetime = pendulum.from_format(val, format_string)
      return to_iso_string(utc_datetime, options.date_only)
    else:
      return None
  # Priority mapping.
  elif colname in ["priority"]:
    if options.flagged_to_high_priority:
      if is_flagged(val):
        return "H"
      else:
        return None
    elif options.flagged_as_tag:
      return val
    else:
      return None
  # These need to be converted to arrays.
  elif colname in ["tags"]:
      if options.context_as_tag and val:
          return [val]
      else:
          return None
  elif colname in ["notes"]:
    if options.export_notes:
      if val:
        return re.sub('\r?\n', NOTES_NEWLINE, val)
      else:
        return val
    else:
      return None
  else:
      return val

def is_flagged(priority):
  return priority != "0"

def is_task(row, transformed_data):
  first_task = "%s.1" % row["project-tree-id"]
  if find_description_by_project_tree_id(first_task, transformed_data):
    return False
  else:
    return True

def has_project_notes(row):
  return "notes" in row and row["notes"]

def find_description_by_project_tree_id(project_tree_id, transformed_data):
  for row in transformed_data:
    if project_tree_id == row["project-tree-id"]:
      return row["description"]

def adjust_project_name(description):
  if options.standardize_project_names:
    return re.sub(r'\W+', '', description.title())
  else:
    return description

def build_project_name(row, transformed_data):
  path = row["project-tree-id"].split(".")
  name_list = []
  path.pop()
  while len(path) > 0:
    project_tree_id = '.'.join(path)
    description = find_description_by_project_tree_id(project_tree_id, transformed_data)
    name_list.append(adjust_project_name(description))
    path.pop()
  name_list.reverse()
  return '.'.join(name_list)

def add_project_note(row, transformed_data):
  row_copy = copy.deepcopy(row)
  # Fake the project-tree-id of a leaf.
  row_copy["project-tree-id"] = "%s.1" % row["project-tree-id"]
  return {
    "uuid": str(uuid.uuid4()),
    "entry": current_time_iso(),
    "project": build_project_name(row_copy, transformed_data),
    "status": "pending",
    "description": "Notes",
    "notes": re.sub('\r?\n', NOTES_NEWLINE, row["notes"]),
  }

def adjust_columns(row, transformed_data):
  row["uuid"] = str(uuid.uuid4())
  row["entry"] = row["end"] if "end" in row and row["end"] else current_time_iso()
  row["project"] = build_project_name(row, transformed_data)
  status = None
  if "end" in row and row["end"]:
    status = "completed"
    row["modified"] = row["end"]
  else:
    status = "pending"
  row["status"] = status
  if "scheduled" in row and options.start_date_is_wait:
    row["wait"] = row["scheduled"]
    row.pop("scheduled")
  if not "description" in row:
    # Taskwarrior requires a description, ensure it.
    row["description"] = "[None]"
  if not options.flagged_to_high_priority and options.flagged_as_tag:
    if is_flagged(row["priority"]):
      if "tags" in row:
        row["tags"].append("flagged")
      else:
        row["tags"] = ["flagged"]
    row.pop("priority")
  if "project" in row and not row["project"]:
    row.pop("project")
  return row

def clean_columns(task_row):
  task_row.pop("project-tree-id")
  return task_row

def transform_row(column_names, row):
  json_row = {}
  for idx, val in enumerate(row):
    colname = None
    try:
      colname = column_names[idx]
    except IndexError:
      print 'Column index %d does not exist in row!' % idx
    if colname and colname in FIELD_MAP and FIELD_MAP[colname]:
      mapped_colname = FIELD_MAP[colname]
      converted_value = convert_column_value(mapped_colname, val)
      if converted_value:
        if options.verbose:
          print 'colname: "%s", field name: "%s", val: "%s"' % (colname, mapped_colname, converted_value)
        json_row[mapped_colname] = converted_value
      else:
        if options.verbose:
          print 'skipping colname: "%s", field name: "%s", val: "%s"' % (colname, mapped_colname, converted_value)
  return json_row

def transform_data(data):
  column_names = None
  transformed_data = []
  for row in data:
    if column_names:
      transformed_row = transform_row(column_names, row)
      transformed_data.append(transformed_row)
    else:
      column_names = row
  return transformed_data

def write_json(data):
  json_string = json.dumps(data)
  json_file.write(json_string + "\n")
  if options.verbose:
    print(json_string)

def generate_json(transformed_data):
  task_rows = []
  project_notes_rows = []
  for row in transformed_data:
    if is_task(row, transformed_data):
      task_rows.append(adjust_columns(row, transformed_data))
    elif options.export_notes and has_project_notes(row):
      project_notes_rows.append(add_project_note(row, transformed_data))
  if options.export_notes:
    for project_notes_row in project_notes_rows:
      write_json(project_notes_row)
  for task_row in task_rows:
    write_json(clean_columns(task_row))

with open(options.output_filename, output_filemode) as json_file:
  with open(options.input_filename, 'rb') as csvfile:
    data = csv.reader(csvfile)
    transformed_data = transform_data(data)
    generate_json(transformed_data)
    print("\nDone! Hopefully everything went well... :)\n")

