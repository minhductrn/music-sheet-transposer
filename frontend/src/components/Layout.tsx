import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="app-shell">
      <main className="app-main">{children}</main>
    </div>
  )
}
