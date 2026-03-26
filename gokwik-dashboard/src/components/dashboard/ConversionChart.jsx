import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts'

const data = [
  { name: 'Completed', value: 68.4, color: '#00b894' },
  { name: 'Abandoned', value: 21.3, color: '#e17055' },
  { name: 'Pending', value: 10.3, color: '#fdcb6e' },
]

const renderLabel = ({ name, value }) => `${value}%`

export default function ConversionChart() {
  return (
    <div className="chart-card">
      <h3>Checkout Funnel</h3>
      <div className="subtitle">Conversion breakdown this month</div>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={65}
            outerRadius={100}
            paddingAngle={4}
            dataKey="value"
            label={renderLabel}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => `${value}%`}
            contentStyle={{ borderRadius: 8, fontSize: 13 }}
          />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            iconSize={8}
            formatter={(value) => <span style={{ fontSize: 13, color: '#636e72' }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
