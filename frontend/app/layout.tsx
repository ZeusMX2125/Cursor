import type { Metadata } from 'next'
import './globals.css'

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
      <body suppressHydrationWarning>{children}</body>
    </html>
  )
}

