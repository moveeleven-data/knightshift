# experiments/

This folder contains self-contained experimental modules that run independently of the main KnightShift pipeline. Each subfolder explores a specific architecture pattern, storage model, or observability concept without impacting production DAGs or container logic.

Use this space to prototype ideas (e.g., document storage, columnar formats, vector embedding, observability, etc.) in isolation. Experiments typically include a dedicated Dockerfile, requirements.txt, and README for reproducibility. They share schema conventions with the core project but are sandboxed to avoid side effects.

Run individual experiments by `cd` into the folder and launching `docker compose up` (if present), or executing any scripts or notebooks included.
