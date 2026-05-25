import re
import os

filepath = r"d:\Dhruv\ARCX_mark-2\arcx-frontend\layout.txt"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Split the content by '----'
blocks = content.split('----')

files = {}

for block in blocks[1:]: # skip the directory tree at the start
    lines = block.strip().split('\n')
    if not lines:
        continue
    
    # find the filename (first non-empty line)
    filename = ""
    start_idx = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('//'):
            filename = line
            start_idx = i + 1
            break
            
    # Some filenames have spaces or comments in the first line in layout.txt
    if filename == "authstore.js":
        target = "src/store/authStore.js"
    elif filename == "app.jsx":
        target = "src/App.jsx"
    elif filename == "applayout.jsx":
        target = "src/components/layout/AppLayout.jsx"
    elif filename == "authpage.jsx":
        target = "src/pages/AuthPage.jsx"
    elif filename == "dashboardpage.jsx":
        target = "src/pages/DashboardPage.jsx"
    elif filename == "walletpage.jsx":
        target = "src/pages/WalletPage.jsx"
    elif filename == "kycpage.jsx":
        target = "src/pages/KYCPage.jsx"
    elif filename == "main.jsx":
        target = "src/main.jsx"
    elif filename == "index.css":
        target = "src/index.css"
    elif filename == "index.html":
        target = "index.html"
    elif filename == "tailwind.config.js":
        target = "tailwind.config.js"
    elif filename == "vite.config.js":
        target = "vite.config.js"
    elif filename == "package.json":
        target = "package.json"
    else:
        # try to parse from comment
        if "main.jsx" in filename: target = "src/main.jsx"
        else: continue

    code = '\n'.join(lines[start_idx:]).strip()
    files[target] = code

base_dir = r"d:\Dhruv\ARCX_mark-2\arcx-frontend"
for target, code in files.items():
    full_path = os.path.join(base_dir, target.replace('/', os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as out:
        out.write(code)
    print(f"Wrote {target}")

