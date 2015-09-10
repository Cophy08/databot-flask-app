import sys, os
virt_binary = "/home/kevinka1/pyenv/bin/python"
if sys.executable != virt_binary: os.execl(virt_binary, virt_binary, *sys.argv)
sys.path.append(os.getcwd())

# Imports databot.py from /app
from app.databot import app as application