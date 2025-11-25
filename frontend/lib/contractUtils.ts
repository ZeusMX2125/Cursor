import type { ProjectXContract } from '@/contexts/ContractsContext'

/**
 * Map ProjectX quote symbol (e.g., "F.US.EP") to contract symbols
 * Returns all matching contracts for a quote symbol
 */
export function mapQuoteSymbolToContracts(
  quoteSymbol: string,
  contracts: ProjectXContract[]
): ProjectXContract[] {
  if (!quoteSymbol || !contracts.length) return []

  const upperQuote = quoteSymbol.toUpperCase()

  // Exact match first
  const exactMatch = contracts.find(
    (c) => (c.symbol || '').toUpperCase() === upperQuote
  )
  if (exactMatch) return [exactMatch]

  // Handle ProjectX quote format: "F.US.EP", "F.US.MES", etc.
  if (upperQuote.includes('.')) {
    const parts = upperQuote.split('.')
    if (parts.length >= 3) {
      const symbolId = parts[2] // EP, MES, NQ, etc.

      // Map common ProjectX symbol IDs to base symbols
      const symbolIdMap: Record<string, string[]> = {
        EP: ['ES', 'MES'], // E-mini S&P 500
        MES: ['MES'],
        ES: ['ES', 'MES'],
        NQ: ['NQ', 'MNQ'], // E-mini NASDAQ
        MNQ: ['MNQ'],
        M2K: ['M2K'], // Micro Russell 2000
        RTY: ['RTY', 'M2K'],
        CL: ['CL'], // Crude Oil
        MGC: ['MGC'], // Micro Gold
        GC: ['GC', 'MGC'], // Gold
      }

      const baseSymbols = symbolIdMap[symbolId] || [symbolId]

      // Find contracts matching any of these base symbols
      return contracts.filter((c) => {
        const contractBase = (c.baseSymbol || c.symbol || '').toUpperCase()
        return baseSymbols.some((base) => contractBase === base.toUpperCase())
      })
    }
  }

  // Try matching by base symbol
  const baseMatches = contracts.filter((c) => {
    const contractBase = (c.baseSymbol || c.symbol || '').toUpperCase()
    return contractBase === upperQuote || upperQuote.includes(contractBase)
  })

  if (baseMatches.length > 0) return baseMatches

  return []
}

/**
 * Check if a quote symbol matches a chart symbol using contract data
 */
export function quoteMatchesChartSymbol(
  quoteSymbol: string,
  chartSymbol: string,
  contracts: ProjectXContract[]
): boolean {
  if (!quoteSymbol || !chartSymbol || !contracts.length) return false

  const upperQuote = quoteSymbol.toUpperCase()
  const upperChart = chartSymbol.toUpperCase()

  // Exact match
  if (upperQuote === upperChart) return true

  // Get chart contract
  const chartContract = contracts.find(
    (c) =>
      (c.symbol || '').toUpperCase() === upperChart ||
      (c.name || '').toUpperCase() === upperChart
  )

  if (!chartContract) return false

  // Check if quote symbol maps to this contract
  const matchingContracts = mapQuoteSymbolToContracts(quoteSymbol, contracts)
  return matchingContracts.some(
    (c) =>
      (c.symbol || '').toUpperCase() === (chartContract.symbol || '').toUpperCase()
  )
}

/**
 * Format symbol for display (convert ES to MES for micro contracts)
 */
export function formatSymbolForDisplay(symbol: string, contract?: ProjectXContract): string {
  if (!symbol) return ''
  
  // If we have contract data, use baseSymbol to determine if it's micro
  if (contract?.baseSymbol) {
    const base = contract.baseSymbol.toUpperCase()
    const symbolUpper = symbol.toUpperCase()
    
    // If it's already MES, return as is
    if (symbolUpper.startsWith('MES')) {
      return symbolUpper
    }
    
    // If base is ES and symbol has contract month code, show as MES
    if (base === 'ES' && symbolUpper.length >= 4) {
      const monthCode = symbolUpper.charAt(2)
      if (monthCode && /[FGHJKMNQUVXZ]/.test(monthCode)) {
        return 'M' + symbolUpper
      }
    }
    
    return symbolUpper
  }
  
  // Fallback to original logic if no contract data
  const upperSymbol = symbol.toUpperCase()
  if (upperSymbol.startsWith('MES')) {
    return upperSymbol
  }
  if (upperSymbol.startsWith('ES') && upperSymbol.length >= 4) {
    const monthCode = upperSymbol.charAt(2)
    if (monthCode && /[FGHJKMNQUVXZ]/.test(monthCode)) {
      return 'M' + upperSymbol
    }
  }
  return upperSymbol
}

/**
 * Get contract description/name for display
 */
export function getContractDisplayName(contract: ProjectXContract | null): string {
  if (!contract) return ''
  return contract.description || contract.name || contract.symbol || ''
}

