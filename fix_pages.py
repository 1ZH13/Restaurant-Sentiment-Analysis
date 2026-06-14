import os
import sys

pages_dir = 'dashboard/pages'

for f in os.listdir(pages_dir):
    if f.endswith('.py') and f != '__init__.py':
        sys.stdout.buffer.write((f + '\n').encode('utf-8'))
