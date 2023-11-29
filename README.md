# Potato

TCP server that talks to postgres using psychopg.

## Development

Install postgresql and follow installation guideline

```bash
brew install postgresql@15
```

Run postgresql

```bash
LC_ALL="C" /usr/local/opt/postgresql@15/bin/postgres -D /usr/local/var/postgresql@15
```

Install backend dependencies

```bash
pip3 install -r requirements.in
```

Run backend

```bash
python3 main.py
```
