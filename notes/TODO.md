# TODO

- [x] Add timings to functions 
- [ ] Write tests for functions
- [x] Add traces to all calls
- [x] Trim summaries to help token limits/truncation
- [x] Speedup ingest_rss_feeds with concurrency
- [ ] Experiment tracking for different models/prompts with MLFlow
- [x] Refactor ingest_rss_feeds to return a list[dict] directly instead of dict[str, list]
- [ ] Refactor the Researcher agent into decomposed functions
- [x] DRY
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
- [ ] Actually do structured output I guess ollama can do this kina like PydanticAI https://docs.ollama.com/capabilities/structured-outputs#python-2
- [ ] It would be cool on my website to host the drafts and revisions process like behind the scenes from like a selector so you could see the diff .. not sure how that would work with htmx
- [ ] Add checkpoints and break up functional outputs so that it doesn't have to run as a continuous 'script' and can be restarted in place.
- [ ] Add agent memory of previously covered articles (so as not to repeat) 
- [ ] Add agent memory of previous digests to learn from past output
