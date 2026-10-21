# Email triage

Every morning (or every N hours) this reads your new Gmail, has a cheap model
sort it, and sends one digest to your phone on Telegram: how many emails came
in, from whom, which ones need you, why, and what to reply.

```
7 emails, 2 need you (Tue 20 Oct 07:00 to Wed 21 Oct 07:00)

By sender: Sam Okafor 1 · Indeed 1 · Flipboard 1 · Big Shop 1 · My Bank 1 · other 2
By type: personal 2 · jobs 1 · newsletter 1 · promotion 1 · other 1 · social 1

Act on
1. Sam Okafor: Confirm you'll be in for the Thursday 10am repair visit [urgent]
   Why: The plumber slot is lost if you don't confirm
   Reply: Thursday 10am works, I'll be in.
2. My Bank: Verify your address by Friday [urgent]
   Why: Your replacement card can't be sent until you do
```

## How it works

Seven stages, each with only the access it needs. No stage that reads email
text holds a credential or a tool, so a malicious email can at worst mislabel
itself; it can't send, delete or forward anything.

| # | Stage | File | Can touch | Model? |
|---|---|---|---|---|
| 1 | Scheduler | cron + `run.sh` | nothing else | no |
| 2 | Fetcher | `triage/stages/fetcher.py` | Gmail, **read-only** scope | no |
| 3 | Pre-sorter | `triage/stages/presort.py` | the fetched emails | no |
| 4 | Classifier | `triage/stages/classifier.py` | only the text it's given | yes (Haiku) |
| 5 | Summariser | `triage/stages/summariser.py` | only the text it's given | yes (Haiku) |
| 6 | Digest builder | `triage/stages/digest.py` | the results | no |
| 7 | Sender | `triage/stages/sender.py` | Telegram token, one fixed chat | no |

- Counting, duplicate removal, Gmail's own Promotions/Social labels and senders
  you list as newsletters are handled by plain code, with no model call.
- Model output must fit a fixed schema (`triage/models.py`) or it's rejected.
- If the model fails on an email, the email still appears in the digest with its
  subject, so nothing disappears silently. If a whole run fails, you get a short
  "digest failed" message instead.
- The local database (`data/triage.db`) keeps run history, digests and
  per-email metadata (sender, category, needed action). It never stores email bodies.
- `tests/test_least_privilege.py` checks that the model-side code can't import
  the mailbox, Telegram, the network or a shell.

### Swapping the model provider

Stages call `Provider.structured(...)`: text in, a validated object out.
`triage/providers/anthropic_provider.py` is the Claude adapter. To add another
vendor, write one subclass of `Provider` and register it in
`triage/providers/__init__.py`, then set `provider = "..."` in `config.toml`.

## Try it without any accounts

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m pytest                 # 17 tests, all offline
python -m triage run --dry-run   # sample emails + fake model, prints a digest
```

## Set up (about 20 minutes, once, all in a browser)

The digest runs in GitHub's cloud on a schedule (`.github/workflows/digest.yml`),
so no computer needs to be on. You only need to create three accounts' worth of
keys and paste them into the repo's secrets: **Settings → Secrets and variables →
Actions → New repository secret**.

**1. Gmail, read-only** (Google requires the account owner to click consent)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project called `email-triage`.
2. APIs & Services → Library → search **Gmail API** → Enable.
3. Google Auth Platform → Branding: app name `email-triage`, your email as support and developer contact.
   Audience: **External**. Data access: add the scope `https://www.googleapis.com/auth/gmail.readonly`.
4. Audience → **Publish app**. If you skip this, Google expires the sign-in every 7 days and the
   digest stops. An unverified app is fine for your own account.
5. Clients → Create client → **Web application**. Under Authorized redirect URIs add
   `https://developers.google.com/oauthplayground`. Copy the client ID and client secret.
6. Open the [OAuth Playground](https://developers.google.com/oauthplayground). Click the gear icon,
   tick **Use your own OAuth credentials**, paste the client ID and secret.
7. In the box under the API list type `https://www.googleapis.com/auth/gmail.readonly`, click
   **Authorize APIs**, sign in, and accept the "unverified app" warning (Advanced → continue).
8. Click **Exchange authorization code for tokens** and copy the refresh token.
9. Add three secrets: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`.

**2. Telegram** (bots can only be created from your own Telegram account)

1. In Telegram, message **@BotFather**, send `/newbot`, pick a name. Save the token as secret `TELEGRAM_BOT_TOKEN`.
2. Message **@userinfobot**; it replies with your numeric id. Save it as secret `TELEGRAM_CHAT_ID`.
3. Send any message to your new bot once, so it is allowed to message you.

**3. Anthropic API key**

Create a key at [platform.claude.com](https://platform.claude.com) → API keys. Save it as secret `ANTHROPIC_API_KEY`.

**4. Test it**

Actions tab → **Email digest** → Run workflow. Pick mode `no-model` first (counts only, proves
Gmail and Telegram work), then `full`. After that it runs by itself at 07:07 UTC daily; edit the
cron line in `.github/workflows/digest.yml` to change it (for every 5 hours: `7 */5 * * *`).

### Running on your own computer instead

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
cp config.example.toml config.toml
mkdir -p secrets && touch secrets/env && chmod 600 secrets/env   # put the same secrets here as KEY=value lines
python -m triage auth      # alternative to the OAuth Playground: needs secrets/credentials.json (Desktop app client)
./run.sh --no-model        # then ./run.sh --print, then ./run.sh
```

Schedule with `crontab -e`: `7 7 * * * /full/path/to/email-triage/run.sh >> /full/path/to/email-triage/data/cron.log 2>&1`.

## Privacy notes

- Gmail access is read-only. Nothing is ever sent, archived or deleted.
- Claude API data is not used for training. Avoid Batch and Files APIs and the
  Fable/Mythos models, which retain data; Haiku and Sonnet are used here.
- Cloud runs happen on GitHub's servers, which see email text while the run lasts; the run log never prints it.
- Telegram's servers see the digest text. Fine for your own inbox; replace it
  before handling anyone else's mail.
- Secrets live only in `secrets/` and environment variables, both git-ignored.
