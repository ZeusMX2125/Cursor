
# Symbol Search Endpoint
@app.get("/api/market/search")
async def search_symbols(query: str = Query(..., min_length=1)):
    """Search for symbols (ProjectX contracts)."""
    if not projectx_service:
        raise HTTPException(status_code=503, detail="ProjectX service not initialized")
    
    try:
        contracts = await projectx_service.search_contracts(search_text=query, live=True)
        # Format for TradingView or generic frontend use
        results = []
        for c in contracts:
            results.append({
                "symbol": c.get("symbol"),
                "description": c.get("name") or c.get("description"),
                "exchange": "TopstepX",
                "type": "futures",
                "contract_id": c.get("id")
            })
        return results
    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        return []

