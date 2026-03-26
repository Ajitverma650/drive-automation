import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const data = [
  { week: 'W1', withGokwik: 3.8, industry: 8.2 },
  { week: 'W2', withGokwik: 4.1, industry: 7.9 },
  { week: 'W3', withGokwik: 3.5, industry: 8.5 },
  { week: 'W4', withGokwik: 4.2, industry: 8.1 },
  { week: 'W5', withGokwik: 3.9, industry: 8.8 },
  { week: 'W6', withGokwik: 3.6, industry: 8.3 },
  { week: 'W7', withGokwik: 4.0, industry: 9.0 },
  { week: 'W8', withGokwik: 3.4, industry: 8.6 },
]

export default function RTOAnalytics() {
  return (
    <div className="chart-card">
      <h3>RTO Rate Comparison</h3>
      <div className="subtitle">GoKwik vs Industry average (% of orders)</div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="week" tick={{ fontSize: 12, fill: '#636e72' }} />
          <YAxis tick={{ fontSize: 12, fill: '#636e72' }} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            formatter={(value) => `${value}%`}
            contentStyle={{ borderRadius: 8, fontSize: 13 }}
          />
          <Line
            type="monotone"
            dataKey="withGokwik"
            stroke="#00b894"
            strokeWidth={2.5}
            dot={{ r: 4 }}
            name="With GoKwik"
          />
          <Line
            type="monotone"
            dataKey="industry"
            stroke="#e17055"
            strokeWidth={2.5}
            strokeDasharray="5 5"
            dot={{ r: 4 }}
            name="Industry Avg"
          />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', gap: 24, justifyContent: 'center', marginTop: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <div style={{ width: 12, height: 3, background: '#00b894', borderRadius: 2 }} />
          <span style={{ color: '#636e72' }}>With GoKwik</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <div style={{ width: 12, height: 3, background: '#e17055', borderRadius: 2, borderTop: '1px dashed #e17055' }} />
          <span style={{ color: '#636e72' }}>Industry Avg</span>
        </div>
      </div>
    </div>
  )
}
