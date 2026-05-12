# Skill: run-pipeline

## Trigger
"run [pipeline name or number] for [brand]" — when no specific pipeline skill matched.

## What to do — no questions
Find the correct pipeline folder from `pipelines/` that matches what the user asked for, instantiate the pipeline class with the brand name and URL the user gave, run it, and show the key output fields. Default URL = https://www.[brand].com if not given.
