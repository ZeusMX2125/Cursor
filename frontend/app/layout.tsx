import type { Metadata } from 'next'
import './globals.css'
import { ContractsProvider } from '@/contexts/ContractsContext'

export const metadata: Metadata = {
  title: 'ALGOX - Algorithmic Trading Bot',
  description: 'TopstepX Automated Trading System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <ContractsProvider>{children}</ContractsProvider>
      </body>
    </html>
  )
}

