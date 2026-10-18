#!/usr/bin/env python3
"""Compile and execute shipped PTY teardown logic without GTK or a phone."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'tools/s10plus/a33/nuxel-pwa-host.c'


def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


class TerminalLifecycle(unittest.TestCase):
    def test_teardown_before_reopen_and_old_child_exit(self):
        text = SOURCE.read_text()
        code = r'''
#include <assert.h>
#include <stddef.h>
typedef int GPid;
typedef int gint;
typedef void *gpointer;
#define SIGHUP 1
static int term_watch=7, term_fd=40, term_pid=100;
static void *term_chan=(void *)1;
static int removed=0, closed=0, killed=0, unrefed=0;
static void g_source_remove(int watch) { assert(watch==7); removed++; }
static void g_io_channel_unref(void *channel) { assert(channel==(void *)1); unrefed++; }
static void close(int fd) { assert(fd==40); closed++; }
static void kill(int pid, int signal) { assert(pid==100 && signal==SIGHUP); killed++; }
static void g_spawn_close_pid(int pid) { (void)pid; }
'''
        code += function(text, 'static void term_request_close(void)')
        code += function(text, 'static void term_child_exited(')
        code += r'''
int main(void) {
  term_request_close();
  assert(removed==1 && closed==1 && killed==1 && unrefed==1);
  assert(term_watch==0 && term_chan==NULL && term_fd==-1 && term_pid==-1);
  term_request_close(); /* repeated close must be harmless */
  assert(removed==1 && closed==1 && killed==1 && unrefed==1);
  term_pid=200; term_fd=50; term_watch=8; /* reopened session */
  term_child_exited(100, 0, NULL); /* old shell reaped after reopen */
  assert(term_pid==200 && term_fd==50 && term_watch==8);
  term_child_exited(200, 0, NULL);
  assert(term_pid==-1);
  return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp)/'lifecycle.c'
            exe = Path(tmp)/'lifecycle'
            c.write_text(code)
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)

    def test_close_ack_precedes_view_destruction(self):
        code = SOURCE.read_text().split('static void on_host_message(', 1)[1].split('static void host_api_attach', 1)[0]
        close = code.split('if (!strcmp(method, "term.close"))', 1)[1].split('return;', 1)[0]
        self.assertLess(close.index('host_reply('), close.index('term_close_window('))


if __name__ == '__main__':
    unittest.main(verbosity=2)
