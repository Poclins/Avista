import io
path = 'tasks.md'
with io.open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
fixed = []
changed = 0
for line in lines:
    try:
        rep = line.encode('cp1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        rep = line
    if rep != line:
        changed += 1
    fixed.append(rep)
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(fixed)
print('changed_lines=%d' % changed)

