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

## Set up for real (about 30 minutes, once)

These steps need your own Google, Telegram and Anthropic accounts.

**1. Config and secrets folder**

```bash
cp config.example.toml config.toml
mkdir -p secrets && touch secrets/env && chmod 600 secrets/env
```

**2. Gmail read-only access** (Google requires you to click consent yourself)

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create a project called `email-triage`.
2. APIs & Services → Library → search **Gmail API** → Enable.
3. Google Auth Platform → Branding/Audience: user type **External**, app name `email-triage`,
   your email as support and developer contact. Under Data access add the scope
   `https://www.googleapis.com/auth/gmail.readonly`. Under Audience add your Gmail address as a test user.
4. Under Audience, click **Publish app**. If you skip this, Google expires the sign-in every 7 days
   and the digest stops. For your own account an unverified app is fine; you'll see a
   "Google hasn't verified this app" warning once, click Advanced → continue.
5. Clients → Create client → **Desktop app** → download the JSON and save it as `secrets/credentials.json`.
6. Run `python -m triage auth`. A browser opens; sign in and allow read access.
   This writes `secrets/token.json`.

**3. Telegram bot** (Telegram only lets you create a bot from your own account)

1. In Telegram, message **@BotFather**, send `/newbot`, pick a name. It replies with a token.
2. Add `TELEGRAM_BOT_TOKEN=<token>` to `secrets/env`.
3. Send any message to your new bot, then run
   `set -a; source secrets/env; set +a; python -m triage telegram-chat-id`
   and add the `TELEGRAM_CHAT_ID=...` line it prints to `secrets/env`.

**4. Anthropic API key**

Create a key at [platform.claude.com](https://platform.claude.com) → API keys and add
`ANTHROPIC_API_KEY=<key>` to `secrets/env`.

**5. Test, then schedule**

```bash
./run.sh --no-model   # counts only, no model cost: proves Gmail and Telegram work
./run.sh --print      # full run, printed here instead of sent
./run.sh              # full run, sent to your phone
```

Then `crontab -e` and add one line (07:07 daily; avoid :00, when lots of jobs start):

```
7 7 * * * /full/path/to/email-triage/run.sh >> /full/path/to/email-triage/data/cron.log 2>&1
```

For every 5 hours instead: `0 */5 * * *`. Cron only runs while the computer is awake,
so for a laptop either keep it on or move this to a small always-on server later.

## Privacy notes

- Gmail access is read-only. Nothing is ever sent, archived or deleted.
- Claude API data is not used for training. Avoid Batch and Files APIs and the
  Fable/Mythos models, which retain data; Haiku and Sonnet are used here.
- Telegram's servers see the digest text. Fine for your own inbox; replace it
  before handling anyone else's mail.
- Secrets live only in `secrets/` and environment variables, both git-ignored.
