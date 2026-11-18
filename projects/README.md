# projects/

Your projects live here, one folder each. **Everything in this folder except this README is git-ignored**, so your
footage settings, marks, renders and notes never get committed, and `git pull` never touches them.

Make one by asking Claude ("start a new project for the clips in D:\Footage\Holiday"), or:

```bash
python engine/new_project.py "Holiday 2026" "D:\Footage\Holiday"
```

Want to try the editor without your own footage first? `python engine/demo.py` makes a `demo` project from generated
test clips.
