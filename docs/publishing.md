# Publishing and verification

Project repository: [aimiaosu-blip/aerospace-ibp-recovery-simulator](https://github.com/aimiaosu-blip/aerospace-ibp-recovery-simulator).

The public repository contains the simulator, synthetic datasets, generated analytics, tests and dashboard build specification. Personal application materials are maintained separately and are not part of this repository.

## Work from the published repository

```bash
git clone https://github.com/aimiaosu-blip/aerospace-ibp-recovery-simulator.git
cd aerospace-ibp-recovery-simulator
python3 -m unittest discover -s tests -v
python3 -m aeroplan --seed 42 --output artifacts
```

The workflow runs the test suite and checks reproducible text exports on Python 3.9 and 3.12. Consult [GitHub Actions](https://github.com/aimiaosu-blip/aerospace-ibp-recovery-simulator/actions) for the actual status of each commit; a supplied workflow alone is not evidence of a passing remote run.

## Publish future changes

Start from a fresh clone or pull the latest changes before editing. Run the tests and regenerate the affected evidence before committing. Push only the intended project files; do not force-push over other work.

```bash
git add <reviewed-project-files>
git commit -m "Describe the planning change"
git push origin main
```

Authenticate through GitHub's own sign-in flow when required. Do not store access tokens in the project.

## Delivery boundaries

- Python, SQLite, generated data, tests and the local HTML summary are implemented and runnable.
- The Power BI deliverable is a four-page build specification plus DAX, a theme and an import helper. No actual PBIX is included, and DAX has not been executed in Power BI Desktop.
- All operational data and business outcomes are synthetic. No real Airbus data or production SAP implementation is claimed.
