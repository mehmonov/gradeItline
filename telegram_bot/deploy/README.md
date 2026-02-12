# Deploy (CI/CD)

GitHub Actions orqali deploy qilinadi.

## GitHub Secrets
Repository Settings → Secrets and variables → Actions → New repository secret:

- `SSH_HOST` = server IP (masalan: 149.102.139.254)
- `SSH_USER` = root
- `SSH_KEY` = private SSH key (PEM)
- `BOT_TOKEN` = Telegram bot token
- `TIMEZONE` = Asia/Tashkent (ixtiyoriy)

## SSH key o‘rnatish
1) Mahalliyda SSH key yarating:
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```
2) Public keyni serverga qo‘shing:
```bash
ssh-copy-id -i ~/.ssh/github_actions.pub root@149.102.139.254
```
3) Private key (`~/.ssh/github_actions`) ni `SSH_KEY` secretga qo‘ying.

## Workflow
`/Users/macbookm2air/Documents/projects/darslik/.github/workflows/deploy.yml`

Push `main` bo‘lsa, kod `/home/telegramyordamchi` ga sync qilinadi, venv o‘rnatiladi, systemd servis restart bo‘ladi.
