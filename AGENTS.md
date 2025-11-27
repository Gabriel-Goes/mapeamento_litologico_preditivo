# AGENTS.md

## Scope
These instructions apply to all files in this directory and its subdirectories.

## Goal
Prioritize cloud-free Aster and Sentinel imagery retrieval and preparation for Gram-Schmidt fusion.

## Data Acquisition
- Always request the latest cloud-masked Sentinel-2 (L2A) tiles and Aster scenes covering the AOI.
- Prefer sources with built-in cloud masks; if missing, run a conservative cloud/shadow mask before use.
- Exclude scenes with >10% cloud cover whenever possible.

## Preprocessing
- Reproject and resample datasets to a common CRS and resolution before fusion.
- Clip to AOI to minimize processing time and storage.

## Fusion Guidance
- Use cloud-free Aster as the multispectral reference and Sentinel-2 bands as the panchromatic surrogate for Gram-Schmidt fusion.
- Verify band alignment and metadata consistency prior to fusion; reject misaligned scenes.

## Hygiene
- Do not commit temporary downloads or intermediate artifacts.
- Keep instructions short and specific; expand only when necessary.
