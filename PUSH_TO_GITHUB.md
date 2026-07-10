# Publish this folder to GitHub

From inside the extracted `CAD` directory:

```bash
git init
git branch -M main
git add .
git commit -m "Add synthetic CAD replication package"
git remote add origin https://github.com/tanhaei/CAD.git
git push -u origin main
```

If the remote repository already contains a commit such as a generated README,
clone it first or pull with an explicit merge/rebase strategy before pushing.
Do not commit restricted BioArc logs, traces, credentials, or patient-linked data.
