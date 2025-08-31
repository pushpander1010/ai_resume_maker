import importlib, sys
mods = ["models","tools","main"]
for m in mods:
    try:
        importlib.import_module(m)
        print(f"Imported {m} OK")
    except Exception as e:
        print(f"ERROR importing {m}: {type(e).__name__}: {e}")
        sys.exit(1)
print("All imports OK")
