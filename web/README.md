# zbot web app

A dashboard for the Zodiac cipher bot. It shows every result in plain language, and lets
you queue the bot's own suggestions, add new tests, and start a run.

- **Reading** needs nothing: results come from the public GitHub repo (the `zbot-results`
  branch the workflow writes, falling back to `results/` on the default branch).
- **Changing things** (Queue, Add, Remove, Run now) needs two environment variables. Without
  them the site works read-only.

## Deploy on Vercel (about 5 minutes)

1. **Import the repo.** On vercel.com, choose *Add New → Project*, pick
   `MisterMcFlyXXVI/Zodiac`, and set **Root Directory** to `web`. Leave the framework as
   Next.js and the build settings at their defaults.
2. **Create a GitHub token** for the buttons. On GitHub, open *Settings → Developer settings
   → Personal access tokens → Fine-grained tokens → Generate new token*:
   - **Repository access:** *Only select repositories* → `Zodiac`
   - **Permissions:** *Contents: Read and write*, *Actions: Read and write* (Metadata:
     read is added automatically)
   - Pick an expiry you're comfortable with. When it expires the buttons stop working
     until you add a new one.
3. **Add environment variables** in Vercel (*Project → Settings → Environment Variables*):

   | Name | Value |
   |---|---|
   | `GITHUB_TOKEN` | the token from step 2 |
   | `ADMIN_PASSWORD` | a password of your choice; it unlocks the buttons |
   | `GITHUB_REPO` | `MisterMcFlyXXVI/Zodiac` (optional; this is the default) |

4. **Deploy** (or *Redeploy*, if you added the variables after the first deploy).

Then open the site, go to **Queue & ideas**, and unlock with your password.

## How the buttons work

| Button | What happens on GitHub |
|---|---|
| Queue this / Add to queue | A JSON file is committed to `hypotheses/queue/` on the default branch. The next run checks it and runs it before the built-in plan. |
| Remove | That file is deleted (only for tests that haven't run). |
| Start a run now | The `zbot` workflow is started (the same as *Actions → zbot → Run workflow*). If a run is going, the new one waits for it. |

Everything you submit is checked twice: by this app before it is committed, and by the bot
(`zbot/schema.py`) before it runs. A bad request is refused with the reason shown on the
Queue page, and never runs.

**Security:** anyone with the URL can *view* results, which are public anyway since the repo
is public. Only someone with `ADMIN_PASSWORD` can change anything. The token never leaves
the server. If the password leaks, change `ADMIN_PASSWORD` in Vercel and redeploy: that
logs everyone out.

## Pages

- **Overview**: the headline, counts, whether the bot is running, calibration per language,
  latest results.
- **Results**: every test, with filters (verdict, cipher, language, alerts), search and sorting.
- **Result detail**: the verdict explained, a chart of the real cipher against shuffled
  copies and genuine-text tests, the best decodes, and exactly what was tested.
- **Queue & ideas**: run the bot, the bot's suggestions, your queue, a form for new tests,
  and the built-in plan.
- **How to read this**: p, power, Holm correction and unicity distance in plain words.

## Develop locally

```bash
cd web
npm install
cp .env.example .env.local     # set LOCAL_RESULTS_DIR=../results to read local files
npm run dev                    # http://localhost:3000
npm test                       # unit tests for statistics and validation
```

`GITHUB_API_URL` can point the app at a fake GitHub API for testing the buttons without
touching the real repo.
