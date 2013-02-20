import cio
import os
import os.path
import sqlite3
import sys
import yaml

# Create data dir if necessary
data_dir = os.path.expanduser(r'~\.apptrigger')
if not os.path.isdir(data_dir): os.mkdir(data_dir)
db_path = os.path.join(data_dir, 'db.sqlite3')

# Initialize DB
if not os.path.isfile(db_path):
  conn = sqlite3.connect(db_path)
  conn.execute('''create table app(id               integer primary key,
                                   name             text    not null,
                                   path             text    unique not null,
                                   launch_cnt       integer not null default 0,
                                   last_launch_time integer not null default 0)''')
else:
  conn = sqlite3.connect(db_path)
cur = conn.cursor()

def getcfg():
  cfg_path = os.path.join(data_dir, 'settings.yaml')
  if not os.path.isfile(cfg_path):
    dirs = ['~']
    cfg = {'extensions': 'lnk exe py', 'dirs_to_parse': dirs}
    with open(cfg_path, 'w') as f:
      yaml.dump(cfg, f)
  else:
    with open(cfg_path, 'r') as f:
      cfg = yaml.load(f)
  return cfg

def scan():
  cfg = getcfg()
  exts = set('.' + e for e in cfg['extensions'].split())
  cur.execute("attach ':memory:' as tmp")
  cur.execute('create table tmp.upd(path text primary key, name text not null)')
  for d in (os.path.expanduser(unicode(d)) for d in cfg['dirs_to_parse']):
    print 'Parsing', d
    for root, dirs, files in os.walk(d):
      for f in files:
        path      = os.path.join(root, f)
        name, ext = os.path.splitext(f)
        if ext in exts:
          cur.execute('insert into upd(path, name) values(?,?)', (path,name))
  with conn:
    cur.execute('insert into app(name, path) select name, path from upd where path not in (select path from app)')

def update_display(width, height, search_str, matches, sel_index):
  assert width > 5
  assert height > 0
  width -= 1
  search_str_prefix = 'app: '
  cio.setcurpos(0, cio.getcurpos().y)
  print '{}{}'.format(search_str_prefix, cio.str_fill(search_str, width - len(search_str_prefix)))
  print
  line_count = 2
  for i, (id, name, path) in enumerate(matches):
    if line_count >= height: break
    fmt_name = cio.str_fill(name, 30)
    fmt_path = cio.str_fill(path, width - len(fmt_name) - 3) # The 3 is for the two spaces and the *
    print '{} {} {}'.format('*' if sel_index == i else ' ', fmt_name, fmt_path)
    line_count += 1
  for _ in range(height - line_count): print ' '*width
  cio.setcurpos(len(search_str_prefix) + len(search_str), cio.getcurpos().y - height)

def search():
  search_str = ''
  sel_index = 0
  init_line = cio.getcurpos().y
  res_limit = 10
  matches = list(cur.execute("select id,name,path from app order by last_launch_time desc limit ?", (res_limit,)))
  while True:
    update_display(cio.get_console_size()[0], res_limit + 3, search_str, matches, sel_index) 
    k = cio.wait_key()

    if ord(k) == 8: # BACKSPACE, erase last char
      search_str = search_str[:-1]
    elif ord(k) == 13: # ENTER, launch
      id,name,path = matches[sel_index]
      with conn:
        cur.execute("update app set launch_cnt=launch_cnt+1, last_launch_time=strftime('%s', 'now') WHERE id=?", (id,))
      os.startfile(path)
      break
    elif ord(k) == 27: # ESC, quit
      break
    elif ord(k) == 224:
      other_k = cio.wait_key()
      if ord(other_k) == 72:
        if sel_index > 0: sel_index -= 1
      elif ord(other_k) == 80:
        if sel_index < len(matches) - 1: sel_index += 1
    else:
      search_str += k
      sel_index = 0

    matches = list(cur.execute("select id,name,path from app where name like ? order by launch_cnt desc limit ?",
                               ('%{}%'.format(search_str), res_limit)))

  cio.setcurpos(0, cio.getcurpos().y + res_limit + 3)

def main():
  if len(sys.argv) == 2 and sys.argv[1] == 'scan':
    scan()
  elif len(sys.argv) == 1:
    search()
  else:
    print 'Usage: apptrigger.py [scan]'

if __name__ == '__main__':
  main()

