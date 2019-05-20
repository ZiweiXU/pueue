import os
import sys
import tempfile

from subprocess import call
from pueue.client.factories import command_factory, print_command_factory


def execute_add(args, root_dir=None):
    """Add a new command to the daemon queue.

    Args:
        args['command'] (list(str)): The actual programm call. Something like ['ls', '-a'] or ['ls -al']
        root_dir (string): The path to the root directory the daemon is running in.
    """

    # We accept a list of strings.
    # This is done to create a better commandline experience with argparse.
    command = ' '.join(args['command'])

    # Send new instruction to daemon
    instruction = {
        'command': command,
        'path': os.getcwd()
    }
    print_command_factory('add')(instruction, root_dir)


def execute_edit(args, root_dir=None):
    """Edit a existing queue command in the daemon.

    Args:
        args['key'] int: The key of the queue entry to be edited
        root_dir (string): The path to the root directory the daemon is running in.
    """
    # Get editor
    EDITOR = os.environ.get('EDITOR', 'vim')
    # Get command from server
    key = args['key']
    status = command_factory('status')({}, root_dir=root_dir)

    # Check if queue is not empty, the entry exists and is queued or stashed
    if not isinstance(status['data'], str) and key in status['data']:
        if status['data'][key]['status'] in ['queued', 'stashed']:
            command = status['data'][key]['command']
        else:
            print("Entry is not 'queued' or 'stashed'")
            sys.exit(1)
    else:
        print('No entry with this key')
        sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(command.encode('utf-8'))
        tf.flush()
        call([EDITOR, tf.name])

        # do the parsing with `tf` using regular File operations.
        # for instance:
        tf.seek(0)
        edited_command = tf.read().decode('utf-8')

    print_command_factory('edit')({
        'key': key,
        'command': edited_command,
    }, root_dir=root_dir)


def execute_depd(args, root_dir=None):
    key = args['key']
    status = command_factory('status')({}, root_dir=root_dir)
    # Check if queue is not empty, the entry exists and is queued or stashed
    if not isinstance(status['data'], str) and key in status['data']:
        if status['data'][key]['status'] in ['queued', 'stashed']:
            command = status['data'][key]['command']
        else:
            print("Entry is not 'queued' or 'stashed'")
            sys.exit(1)
    else:
        print('No entry with this key')
        sys.exit(1)

    print_command_factory('depd')({
        'key': key,
        'depd': args['depd'],
    }, root_dir=root_dir)
