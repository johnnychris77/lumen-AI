# Deployment Troubleshooting

## API Health Fails

Check logs and confirm:

- app binds to 0.0.0.0
- port is correct
- DATABASE_URL is valid
- Redis URL is valid
- dependencies installed

## Connection Reset by Peer

Usually means the API process starts and then crashes.

Check:

docker logs --tail=160 lumen-ai-api-1

## Dashboard Shows Zeros

Run:

backend/scripts/seed-demo-data.sh

## Static Landing Page Port 9090 Fails

If port 9090 is already in use, either open the existing page or use another port:

python -m http.server 9091 -d docs/public-demo

Then open:

http://127.0.0.1:9091
