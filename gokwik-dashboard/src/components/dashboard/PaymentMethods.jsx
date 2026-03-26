import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const data = [
  { method: 'UPI', orders: 5420, percentage: 42.2 },
  { method: 'Cards', orders: 3210, percentage: 25.0 },
  { method: 'COD', orders: 2140, percentage: 16.6 },
  { method: 'Wallets', orders: 1280, percentage: 10.0 },
  { method: 'Net Banking', orders: 797, percentage: 6.2 },
]

export default function PaymentMethods() {
  return (
    <div className="chart-card">
      <h3>Payment Methods</h3>
      <div className="subtitle">Distribution of payment modes</div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} layout="vertical" barSize={18}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12, fill: '#636e72' }} />
          <YAxis
            type="category"
            dataKey="method"
            tick={{ fontSize: 13, fill: '#2d3436' }}
            width={85}
          />
          <Tooltip
            formatter={(value) => [value.toLocaleString(), 'Orders']}
            contentStyle={{ borderRadius: 8, fontSize: 13 }}
          />
          <Bar dataKey="orders" fill="#6c5ce7" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
