import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Music Sheet Transposer</h1>
      </header>
      <main className="app-main">{children}</main>
    </div>
  )
}
