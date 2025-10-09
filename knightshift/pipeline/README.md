### Pipeline Runners

Modular orchestrator scripts for running individual pipeline stages.

#### Scripts:

`run_ingestion.py`: Runs Lichess TV game ingestion.

`run_cleaning.py`: Executes game record validation and cleanup.

`run_enrichment.py`: Enriches game data with user profiles.

These are useful for DAGs, cron, or manual runs.
