import {
  LayoutDashboard,
  ShoppingCart,
  CreditCard,
  BarChart3,
  Users,
  Settings,
  Package,
  ArrowLeftRight,
  HelpCircle,
  LogOut,
  FileText,
} from 'lucide-react'

const navItems = [
  { section: 'Main' },
  { icon: LayoutDashboard, label: 'Dashboard', page: 'dashboard' },
  { icon: FileText, label: 'Rate Capture', page: 'rateCapture' },
  { icon: ShoppingCart, label: 'Orders' },
  { icon: CreditCard, label: 'Payments' },
  { icon: Package, label: 'Products' },
  { section: 'Analytics' },
  { icon: BarChart3, label: 'Reports' },
  { icon: ArrowLeftRight, label: 'Transactions' },
  { icon: Users, label: 'Customers' },
  { section: 'Settings' },
  { icon: Settings, label: 'Configuration' },
  { icon: HelpCircle, label: 'Help Center' },
]

export default function Sidebar({ onNavigate, currentPage }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">G</div>
        <h2>GoKwik</h2>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item, i) =>
          item.section ? (
            <div key={i} className="nav-section">{item.section}</div>
          ) : (
            <div
              key={i}
              className={`nav-item ${item.page && currentPage === item.page ? 'active' : ''}`}
              onClick={() => item.page && onNavigate(item.page)}
            >
              <item.icon />
              <span>{item.label}</span>
            </div>
          )
        )}
      </nav>
      <div className="nav-item" style={{ borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 'auto' }}>
        <LogOut />
        <span>Logout</span>
      </div>
    </aside>
  )
}
