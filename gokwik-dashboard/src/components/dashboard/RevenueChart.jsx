import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const data = [
  { date: 'Mar 1', revenue: 18.2, orders: 1420 },
  { date: 'Mar 4', revenue: 22.5, orders: 1680 },
  { date: 'Mar 7', revenue: 19.8, orders: 1540 },
  { date: 'Mar 10', revenue: 28.1, orders: 2100 },
  { date: 'Mar 13', revenue: 24.6, orders: 1890 },
  { date: 'Mar 16', revenue: 31.2, orders: 2340 },
  { date: 'Mar 19', revenue: 27.4, orders: 2050 },
  { date: 'Mar 22', revenue: 35.8, orders: 2680 },
  { date: 'Mar 25', revenue: 32.1, orders: 2410 },
  { date: 'Mar 28', revenue: 38.5, orders: 2890 },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: '#1e1e2d',
        padding: '12px 16px',
        borderRadius: 8,
        color: '#fff',
        fontSize: 13,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>{label}</div>
        <div style={{ color: '#a29bfe' }}>Revenue: ₹{payload[0].value}L</div>
        <div style={{ color: '#00b894', marginTop: 2 }}>Orders: {payload[1]?.value}</div>
      </div>
    )
  }
  return null
}

export default function RevenueChart() {
  return (
    <div className="chart-card" style={{ gridColumn: 'span 1' }}>
      <h3>Revenue Trend</h3>
      <div className="subtitle">Daily GMV across all merchants</div>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6c5ce7" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6c5ce7" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#636e72' }} />
          <YAxis tick={{ fontSize: 12, fill: '#636e72' }} tickFormatter={(v) => `₹${v}L`} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#6c5ce7"
            strokeWidth={2.5}
            fill="url(#colorRevenue)"
          />
          <Area
            type="monotone"
            dataKey="orders"
            stroke="#00b894"
            strokeWidth={0}
            fill="transparent"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
