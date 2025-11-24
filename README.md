# TopstepX Algorithmic Trading Bot

Production-grade, fully automated trading system for TopstepX that trades Micro E-mini futures (MNQ, MES, MGC) profitably while strictly adhering to Topstep's $50K Combine account rules.

## Project Structure

```
├── backend/          # Python FastAPI backend
├── frontend/         # Next.js React frontend
├── config/           # Configuration files
└── docker/          # Docker configuration
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ with TimescaleDB extension
- Docker & Docker Compose (optional)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your TopstepX API credentials:

```bash
cp config/.env.example config/.env
```

### Running with Docker

```bash
docker-compose up -d
```

## Development

See the master plan document for detailed implementation phases and architecture.

## License

Proprietary - Internal Use Only

