# Contributing

Contributions that ask a focused question of public astronomical data are welcome.

## Propose an analysis

Open an issue with:

- the scientific question;
- the archive, survey, or instrument;
- the intended measurement and uncertainty estimate;
- one paper or archive document for comparison;
- any access limits, large downloads, or special computing needs.

## Add a notebook

Use a dated folder under the matching archive:

```text
archive-name/YYYY-MM-DD-short-analysis-name/
```

Follow [NOTEBOOK_STANDARD.md](NOTEBOOK_STANDARD.md). Keep checked-in data products small, retain the archive query or product identifier, and execute the notebook before opening a pull request. Never commit private credentials or data that cannot be redistributed.

## Local checks

```bash
python -m pip install -r requirements.txt
python tools/run_notebooks.py --date YYYY-MM-DD
python tools/validate_repository.py
python tools/build_catalog.py
cd dashboard && npm install && npm run build
```

In the pull request, summarize the numerical result, the main limitation, and how it compares with published work.
