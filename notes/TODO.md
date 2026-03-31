# TODO

- [x] Add timings to functions 
- [ ] Add traces to all calls
- [x] Trim summaries to help token limits/truncation
- [ ] Speedup ingest_rss_feeds with concurrency
- [ ] Experiment tracking for different models/prompts with MLFlow
- [ ] Map reduce for articles researcher needs to summarize them for the writer
- [ ] Refactor ingest_rss_feeds to return a list[dict] directly instead of dict[str, list]
- [ ] DRY
- [x] Logging to file
- [ ] Change environment vars to click CLI options
- [x] Add HTTP page request and parse function
- [ ] Add tool calling to writer/editor
- [x] isolate prompts into their own file
- [ ] use pydantic for basic settings 
    ```python
    from pydantic_settings import BaseSettings
    class Settings(BaseSettings):
        db_url: str = "default_url"
    settings = Settings()
    ```

    In other files:
    ```python
    from config import settings
    print(settings.db_url)
    ```