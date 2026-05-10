# LumenAI Demo Mode

Demo Mode loads realistic sample data so the executive dashboard opens with meaningful portfolio activity instead of empty metrics.

## Run

docker compose -f docker-compose.prod.yml up -d --build

backend/scripts/seed-demo-data.sh

Open:

http://127.0.0.1:18011/api/executive-briefing-dashboard/view
