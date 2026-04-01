# AI - Digests

Daily newsletters on AI/ML/DevOps topics from k8s to Agentic Workflows!

> These are now available to view on my website! https://sean-michael.dev/digest

Inspired by a comment Addy Osmani made in his recent chat with Tim O'Reilly on agentic AI systems, where he proposed one could create an AI Agent to stay on top of all the latest innovations in the space.

I thought this was very apt because I would like to experiment with agentic systems more AND I find that I struggle with FOMO whenever new technologies come around.

So the plan is to self host the LLM component using ollama for inference. 

## Agents

I want to build three kinds of agents to work together:

1. The Researcher

    This agent will parse my RSS feeds (eventually maybe a researcher will comb websites) and grab things that seem interesting, recent announcements, model launches, things like that.

2. The Writer

    This agent will take the latest curated findings, dive deeper into them, and draft a newsletter breaking down the most interesting headlines and giving the information needed to learn something or decide if I want to pursue the topic further and read the source material(s).

3. The Editor

    This agent will review the newsletter draft edition from the writer and give feedback. The criteria for a good newsletter will be some balance of succinctness in form: easily parsable, quick 5 minute coffee read, and quality of topics covered as they relate to *my* interests.

## The Loop

I'm picturing a pretty straightforward loop that follows how a human team might approach the issue.

1. The researcher gathers a daily report on a cron, luckily since everyone in this team works so fast the researcher won't have to stay up late or wake up super early, it can likely run maybe 5 minutes before the writer needs to do it's thing.

2. The writer takes this report and begins isolating the stories it wants to cover in depth, creating a first draft.

3. The editor reads the first draft, provides critique, and prompts the writer for a revised draft.

4. The writer revises the draft and submits to the editor.

5. Repeat steps `3` and `4` until either:

    a.) The editor responds with no comments ("LGTM!")

    b.) *n* number of iterations have passed.. not sure how many this should be yet maybe like 4? This is where some experiment tracking is needed to find an optimal number of iterations.

6. The final draft is copied to an S3 bucket where my [personal website](https://sean-michael.dev)) will serve it as a daily edition.

## Beyond RSS

Not everything is available in a nice RSS feed and I will have to do some browser automation or maybe just some simple wgetting to get more blogs and technical reviews and documentation.

I'll just keep a running list of things that are in the works..

- [Anthropic Engineering](https://www.anthropic.com/engineering)

## Local Development

Start phoenix to gather traces:

```bash
docker run -p 6006:6006 -p 4317:4317 -i -t arizephoenix/phoenix:latest
```

Start the Agents:

```bash
uv run main.py
```

