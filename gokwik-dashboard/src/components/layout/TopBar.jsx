import { Search, Bell, Moon } from 'lucide-react'

export default function TopBar() {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1>Dashboard</h1>
        <p>Welcome back! Here's your checkout performance overview.</p>
      </div>
      <div className="topbar-right">
        <div className="search-box">
          <Search size={16} color="#636e72" />
          <input type="text" placeholder="Search orders, merchants..." />
        </div>
        <button className="icon-btn">
          <Moon size={18} />
        </button>
        <button className="icon-btn">
          <Bell size={18} />
          <span className="notification-dot"></span>
        </button>
        <div className="avatar">AJ</div>
      </div>
    </header>
  )
}
