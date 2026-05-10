# LumenAI Demo Mode

Demo Mode loads realistic sample data so the executive dashboard opens with meaningful portfolio activity instead of empty metrics.

## Run Demo Mode

Start the stack:

docker compose -f docker-compose.prod.yml up -d --build

Run:

backend/scripts/seed-demo-data.sh

Expected:

DEMO DATA SEED COMPLETE

Open:

http://127.0.0.1:18011/api/executive-briefing-dashboard/view
