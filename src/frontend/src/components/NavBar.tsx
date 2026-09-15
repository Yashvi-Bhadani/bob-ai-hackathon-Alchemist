/**
 * Shared navigation bar for all pages.
 * Provides consistent header + nav links across Dashboard, Detail, and Simulator pages.
 */
import { Link, useLocation } from 'react-router-dom'

export function NavBar() {
  const { pathname } = useLocation()

  const links = [
    { to: '/', label: 'DASHBOARD' },
    { to: '/simulator', label: 'SIMULATOR' },
  ]

  const isActive = (to: string) =>
    to === '/' ? pathname === '/' || pathname === '/dashboard' : pathname.startsWith(to)

  return (
    <header className="border-b border-border bg-panel px-6 py-3 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-4">
        <div className="w-2 h-2 rounded-full bg-accent animate-pulse flex-shrink-0" />
        <Link to="/" className="text-accent font-semibold tracking-wider text-sm uppercase hover:text-white transition-colors">
          Fab Risk Advisor
        </Link>
        <span className="text-muted text-xs border border-border rounded px-2 py-0.5 flex-shrink-0">
          ⚠ DEMO DATA
        </span>
        <nav className="flex items-center gap-1 ml-2">
          {links.map(l => (
            <Link
              key={l.to}
              to={l.to}
              className={`text-xs px-3 py-1 rounded border font-mono transition-colors ${
                isActive(l.to)
                  ? 'border-accent bg-accent/10 text-accent'
                  : 'border-border text-muted hover:border-gray-500 hover:text-gray-300'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted">
        <span>IBM Bob AI Integration</span>
        <div className="w-1.5 h-1.5 rounded-full bg-success" />
      </div>
    </header>
  )
}
