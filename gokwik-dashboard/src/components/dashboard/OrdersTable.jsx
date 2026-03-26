const orders = [
  { id: 'GK-78234', merchant: 'BoAt Lifestyle', amount: '₹4,599', method: 'UPI', status: 'success', date: '24 Mar 2026' },
  { id: 'GK-78233', merchant: 'Mamaearth', amount: '₹1,299', method: 'Card', status: 'success', date: '24 Mar 2026' },
  { id: 'GK-78232', merchant: 'Lenskart', amount: '₹3,890', method: 'COD', status: 'pending', date: '24 Mar 2026' },
  { id: 'GK-78231', merchant: 'Sugar Cosmetics', amount: '₹899', method: 'UPI', status: 'failed', date: '23 Mar 2026' },
  { id: 'GK-78230', merchant: 'The Man Company', amount: '₹1,649', method: 'Wallet', status: 'success', date: '23 Mar 2026' },
  { id: 'GK-78229', merchant: 'Bewakoof', amount: '₹799', method: 'Card', status: 'refunded', date: '23 Mar 2026' },
  { id: 'GK-78228', merchant: 'Plum Goodness', amount: '₹1,450', method: 'UPI', status: 'success', date: '22 Mar 2026' },
]

export default function OrdersTable() {
  return (
    <div className="table-card">
      <div className="table-header">
        <h3>Recent Orders</h3>
        <span className="view-all">View All →</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Merchant</th>
            <th>Amount</th>
            <th>Payment</th>
            <th>Status</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td style={{ fontWeight: 600, color: '#6c5ce7' }}>{order.id}</td>
              <td>{order.merchant}</td>
              <td style={{ fontWeight: 500 }}>{order.amount}</td>
              <td>{order.method}</td>
              <td>
                <span className={`status-badge ${order.status}`}>
                  {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                </span>
              </td>
              <td style={{ color: '#636e72' }}>{order.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
