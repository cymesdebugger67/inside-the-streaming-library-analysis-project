# Source Provenance and Acquisition

**Project owner:** Cyril James Lunzaga

## Primary source

Ruchi Bhatia, *Movies on Netflix, Prime Video, Hulu and Disney+*, Kaggle:
https://www.kaggle.com/datasets/ruchi798/movies-on-netflix-prime-video-hulu-and-disney

Kaggle lists the dataset under CC0: Public Domain. The dataset contains historical scraped platform-listing metadata, not current 2026 catalogues. The available Kaggle listing and archived copies differ in structure; this project specifically audits the 17-field historical CSV (including an unnamed index-like column).

## Archival retrieval location

SalimAmarti, `OTT_movies_Project`, GitHub archive:
https://github.com/SalimAmarti/OTT_movies_Project/blob/master/MoviesOnStreamingPlatforms_updated.csv

Raw download:
https://raw.githubusercontent.com/SalimAmarti/OTT_movies_Project/master/MoviesOnStreamingPlatforms_updated.csv

The GitHub repository attributes the original dataset to Ruchi Bhatia. The copy is a third-party archive; its exact relationship to the current Kaggle version must not be assumed. The acquisition script records SHA-256 and schema before research use.

## Source restrictions

- This is a historical snapshot, commonly referenced around 2020; its exact as-of date is not independently verified.
- Do not claim that a title is currently available on a named platform.
- Do not infer actual subscribers, viewing demand, revenue, recommendations shown to users, or business strategy.
- Platform flags describe a historical scraped listing. Metadata fields may be incomplete, biased, or inconsistent.
- IMDb and Rotten Tomatoes metrics are optional metadata, with substantial nonrandom missingness possible.
- Do not publish the raw downloaded CSV. Publish transformations, aggregate tables, and source acquisition instructions after review.

## Source reproducibility

Acquisition must record the exact input-file SHA-256, source URL, retrieval date and expected columns. If the source changes, rerun viability checks before interpreting any findings.

## Licence boundary

Kaggle labels the source CC0, but this does not establish ownership or licensing for external ratings, trademarks, underlying movie titles, or other third-party metadata. Use citation and limited analytical outputs; review any redistribution requirements before release.
