import {
  ShoppingCart,
  TrendingUp,
  TrendingDown,
  CreditCard,
  IndianRupee,
  Users,
} from 'lucide-react'

const kpis = [
  {
    label: 'Total GMV',
    value: '₹2.4 Cr',
    trend: '+12.5%',
    trendDir: 'up',
    icon: IndianRupee,
    color: 'purple',
  },
  {
    label: 'Checkout Conversions',
    value: '68.4%',
    trend: '+3.2%',
    trendDir: 'up',
    icon: ShoppingCart,
    color: 'green',
  },
  {
    label: 'Total Orders',
    value: '12,847',
    trend: '+8.1%',
    trendDir: 'up',
    icon: CreditCard,
    color: 'blue',
  },
  {
    label: 'RTO Rate',
    value: '4.2%',
    trend: '-1.8%',
    trendDir: 'up',
    icon: Users,
    color: 'orange',
  },
]

export default function KpiCards() {
  return (
    <div className="kpi-grid">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="kpi-card">
          <div className="kpi-header">
            <div className={`kpi-icon ${kpi.color}`}>
              <kpi.icon size={22} />
            </div>
            <div className={`kpi-trend ${kpi.trendDir}`}>
              {kpi.trendDir === 'up' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {kpi.trend}
            </div>
          </div>
          <div className="kpi-value">{kpi.value}</div>
          <div className="kpi-label">{kpi.label}</div>
        </div>
      ))}
    </div>
  )
}
