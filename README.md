# Export OmniFocus data to Taskwarrior

**WARNING:** *This project is provided as a courtesy and convenience for those
that are looking to move their data from
[OmniFocus](https://www.omnigroup.com/omnifocus) to
[Taskwarrior](https://taskwarrior.org) -- no claim is made that it will work
for you, or that your data will be converted in a manner that satisfies you,
and no unpaid support will be provided. See the [support](#support) section
below for more details.*

This script is best suited for those that aren't afraid to dig into the code
when things don't work right the first time!

### Requirements

 * Python >= 2.7.x
 * [pendulum](https://pendulum.eustace.io/)

### Usage

#### In OmniFocus

 1. Configure the 'Outline' section to contain those items you want exported
   * Only those items that are visible are exported, so if your Perspective is
     configured to hide items that you want exported, make the necessary
     adjustments
   * The export mode will depend on the 'Project hierarchy' setting you have
     enabled. For a flat list of actions with no associated projects, disable
     the hierarchy, for a hierarchical project list of actions, enable the
     hierarchy. See below for more information on how the hierarchy is exported
     into a format Taskwarrior can work with.

 2. Select ```File -> Export...``` from the top menu, and export the file as
    CSV.

#### On the machine running the Taskwarrior client:

 1. Load the CSV file to the machine with Taskwarrior installed, along with the
    ```omnifocus-to-taskwarrior.py``` script.

 2. Make sure ```omnifocus-to-taskwarrior.py``` is executable then run
    ```omnifocus-to-taskwarrior.py -h``` to see the list of available arguments
    for the script.

 3. Run the script with your chosen arguments to generate a JSON file format
    suitable for import by Taskwarrior. If you get any errors, you're on your
    own to figure it out ;)

 4. The generated JSON file is fairly easy to inspect to see if the data is
    coming out the way you want it. The
    [Taskwarrior JSON format specification](https://taskwarrior.org/docs/design/task.html)
    can help guide you.

 5. Import the data into Taskwarrior via: ```task import [json_filename]```,
    and for heaven's sake make a backup of any existing Taskwarrior data
    beforehand!

### Supported data conversions

```
  Task ID -> Used to programmatically calculate project/subproject hierarchy
  Type -> Not used, project/task status calculated by hierarchy
  Name -> description
  Status -> Not used, calculated from other values
  Project -> Not used, calculated from other values
  Context -> tags (optional)
  Start Date -> scheduled ('wait' optional)
  Due Date -> due
  Completion Date -> end
  Duration -> Not currently used
  Flagged -> priority (H) or 'flagged' tag (optional)
  Notes -> notes (optional)
```

#### How project hierarchies are calculated

OmniFocus and Taskwarrior have different approaches to how projects and
actions (tasks) are organized, and this requires that some adjustments
be made in the translation.

Taskwarrior cannot have projects with no tasks, nor does it have any
outlining capability for tasks (tasks can be made 'dependant' on other tasks,
but not simply live beneath other tasks in an outline fashion).

If you choose to keep a project hierarchy, here's what you need to know about
the conversion:

 * Only those items at the very deepest part of a particular hierarchy (the
   'leaves') are considered to be tasks.
 * Everything else is either a top-level project, or if it's somewhere under
   a top-level project, it is a subproject via Taskwarrior's dot notation
   (eg. MyProject.MySubproject)
 * If notes are exported, any notes attached to something determined to be a
   project or subproject will have a task created under that particular project
   or subproject with a description of 'Notes'

The bottom line is that if you have really deep nesting and you use the
project hierarchy, you could end up with unusably long project names. The
rational options in this case seem to be:

 1. Flatten out your hierarchy more
 2. Use short names for projects/subprojects

### Other caveats

 * Notes - Taskwarrior doesn't have proper multiline notes, so if notes are exported,
   they live in a 'notes' [UDA](https://taskwarrior.org/docs/udas.html). Also due to
   [this current bug](https://github.com/GothenburgBitFactory/taskwarrior/issues/2107),
   all newlines are replaced by a ```###NEWLINE###``` token, and you'll have to figure
   out how to deal with making that easily displayable/editable. I currently use the
   [OneNote](https://github.com/thehunmonkgroup/onenote) script I wrote. :)
 * Context - Hierarchical contexts are not exported, only the final context in the hierarchy
 * Folders - Not exported, if you want to keep that hierarchy, turn it into a project
   in OmniFocus

## Support

The issue tracker for this project is provided to file bug reports, feature
requests, and project tasks -- support requests are not accepted via the issue
tracker. For all support-related issues, including configuration, usage, and
training, consider hiring a competent consultant.

It's unlikely that I will add any more features, unless they are accompanied
by a pull request. Bug fixes are a possibility, if they don't involve a crazy
amount of work.
