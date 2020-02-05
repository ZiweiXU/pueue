"""Queue implementation."""
import os
import pickle


class Queue():
    """The task queue representation.

    All tasks, task states and process outputs are stored inside.
    """

    def __init__(self, config_dir):
        """Create a new queue and initialize it with a previous queue, if existing."""
        self.config_dir = config_dir
        self.read()
        self.clean()
        if len(self.queue) > 0:
            self.next_key = max(self.queue.keys()) + 1
        else:
            self.next_key = 0

    def keys(self):
        """Return queue keys."""
        return self.queue.keys()

    def __len__(self):
        """Length information about the queue."""
        return len(self.queue)

    def __getitem__(self, key):
        """Get an item from the queue."""
        return self.queue[key]

    def __setitem__(self, key, value):
        """Set an item from the queue."""
        self.queue[key] = value

    def __delitem__(self, key):
        """Delete an item from the queue."""
        del self.queue[key]

    def items(self):
        """Get all items from the queue."""
        return self.queue.items()

    def get(self, key):
        """Get an item from the queue."""
        return self.queue.get(key)

    def reset(self):
        """Reset the queue."""
        self.queue = {}
        self.next_key = 0
        self.write()

    def clean(self):
        """Clean queue items from a previous session.

        In case a previous session crashed and there are still some running
        entries in the queue ('running', 'stopping', 'killing'), we clean those
        and enqueue them again.
        """
        for _, item in self.queue.items():
            if item['status'] in ['paused', 'running', 'stopping', 'killing']:
                item['status'] = 'queued'
                item['start'] = ''
                item['end'] = ''

    def clear(self):
        """Remove all completed tasks from the queue."""
        for key in list(self.queue.keys()):
            if self.queue[key]['status'] in ['done', 'failed']:
                del self.queue[key]
        self.write()

    def next(self):
        """Get the next processable item of the queue.

        A processable item is supposed to have the status `queued`.

        Returns:
            None : If no key is found.
            Int: If a valid entry is found.

        """

        def _depd_ok(key):
            if 'depd' not in self.queue[key].keys():
                return True
            if 'depd' in self.queue[key].keys() and self.queue[key]['depd'] == [-1]:
                return True
            ok = True
            for d_key in self.queue[key]['depd']:
                if d_key in self.queue.keys():
                    ok = ok and self.queue[d_key]['status'] == 'done'
            return ok

        smallest = None
        for key in self.queue.keys():
            if self.queue[key]['status'] == 'queued':
                if _depd_ok(key):
                    if smallest is None or key < smallest:
                        smallest = key
        return smallest

    def read(self):
        """Read the queue of the last pueue session or set `self.queue = {}`."""
        queue_path = os.path.join(self.config_dir, 'queue')
        if os.path.exists(queue_path):
            queue_file = open(queue_path, 'rb')
            try:
                self.queue = pickle.load(queue_file)
            except Exception:
                print('Queue file corrupted, deleting old queue')
                os.remove(queue_path)
                self.queue = {}
            queue_file.close()
        else:
            self.queue = {}

    def write(self):
        """Write the current queue to a file. We need this to continue an earlier session."""
        queue_path = os.path.join(self.config_dir, 'queue')
        queue_file = open(queue_path, 'wb+')
        try:
            pickle.dump(self.queue, queue_file, -1)
        except Exception:
            print('Error while writing to queue file. Wrong file permissions?')
        queue_file.close()

    def add_new(self, command):
        """Add a new entry to the queue."""
        self.queue[self.next_key] = command
        self.queue[self.next_key]['status'] = 'stashed'
        self.queue[self.next_key]['returncode'] = ''
        self.queue[self.next_key]['stdout'] = ''
        self.queue[self.next_key]['stderr'] = ''
        self.queue[self.next_key]['start'] = ''
        self.queue[self.next_key]['end'] = ''
        self.queue[self.next_key]['depd'] = [-1]

        self.next_key += 1
        self.write()

    def remove(self, key):
        """Remove a key from the queue, return `False` if no such key exists."""
        if key in self.queue:
            del self.queue[key]
            self.write()
            return True
        return False

    def restart(self, key):
        """Restart a previously finished entry."""
        if key in self.queue:
            if self.queue[key]['status'] in ['failed', 'done']:
                new_entry = {'command': self.queue[key]['command'],
                             'path': self.queue[key]['path']}
                self.add_new(new_entry)
                self.write()
                return True
        return False

    def switch(self, first, second):
        """Switch two entries in the queue. Return False if an entry doesn't exist."""
        allowed_states = ['queued', 'stashed']
        if first in self.queue and second in self.queue \
                and self.queue[first]['status'] in allowed_states\
                and self.queue[second]['status'] in allowed_states:

            tmp = self.queue[second].copy()
            self.queue[second] = self.queue[first].copy()
            self.queue[first] = tmp
            self.write()
            return True
        return False
