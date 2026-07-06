# gh-bounty-scout 🕵️💰

CLI tool care scanează GitHub și găsește issue-uri cu **bounties, recompense și premii**.  
Fără dependințe externe — doar Python stdlib.

```bash
# Scanează și arată doar bounties noi
gh-bounty-scout.py scan

# Watch mode — scanează la fiecare 60s
gh-bounty-scout.py watch

# Arată statistici
gh-bounty-scout.py stats
```

## Instalare

```bash
curl -sL https://raw.githubusercontent.com/returntotor/gh-bounty-scout/main/gh-bounty-scout.py -o /usr/local/bin/gh-bounty-scout
chmod +x /usr/local/bin/gh-bounty-scout
```

Sau direct:

```bash
git clone https://github.com/returntotor/gh-bounty-scout.git
cd gh-bounty-scout
./gh-bounty-scout.py scan
```

## Token GitHub

Fără token: 60 req/h (suficient pentru ~7 scanări)
Cu token: 5.000 req/h

```bash
export GITHUB_TOKEN="ghp_..."
```

Sau adaugă în `~/.bashrc` sau `~/.env`.

## Comenzi

| Comandă | Efect |
|---------|-------|
| `scan` | Scanează, arată doar bounties noi |
| `scan --all` | Arată toate bounties găsite |
| `scan --labels` | Afișează și etichetele |
| `scan --pages 5` | Caută mai multe pagini (def: 2) |
| `watch` | Watch mode la 60s |
| `watch --interval 30` | Watch mode la 30s |
| `stats` | Statistici scanări |
| `clear-cache` | Golește cache-ul |

## Output

```
 ═══ NOU: 3 bounties ═══

        $  TITLE                                                           REPO                                   AGE
 ─────  ──────────────────────────────────────────────────────────────  ────────────────────────────────  ────────
  1  $200  GitHub Based Marketing                                          ubiquity/business-development     17d ago
  2   $50  Fix broken file upload in React                                 user/react-app                    2h ago
  3   $30  Add TypeScript types to API client                              org/api-client                    5h ago
 ─────  ──────────────────────────────────────────────────────────────  ────────────────────────────────  ────────
 Total: 3 bounties, 2 cu $ ($250 sum)
```

## Cum funcționează

Caută issue-uri deschise cu label-urile:
- `bounty`, `Price: *`, `prize`, `reward`
- Sau cu sume de bani în titlu (`$XX`)

Extrage automat suma din titlu, corpul issue-ului și etichete.

## License

MIT

---

**Făcut cu Claude Code + Hermes Agent**

Dacă tool-ul ăsta te-a ajutat să faci bani, poți susține proiectul:

## Donations 💰

```
BTC:  bc1qvp20lz33hgwuka5txqtj6schrpvjkeytev0fp6
ETH:  0x1E99D4e3b0A5030bFE55337314c77504938f6fa0
SOL:  8kYx29q4T9ZE7noBPCdMGwbUwcBKj4io2e17z3A7WMQG
```

