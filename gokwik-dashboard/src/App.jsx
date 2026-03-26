import { useState } from 'react'
import './App.css'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import KpiCards from './components/dashboard/KpiCards'
import RevenueChart from './components/dashboard/RevenueChart'
import ConversionChart from './components/dashboard/ConversionChart'
import OrdersTable from './components/dashboard/OrdersTable'
import PaymentMethods from './components/dashboard/PaymentMethods'
import RTOAnalytics from './components/dashboard/RTOAnalytics'
import RateCapture from './components/rate-capture/RateCapture'

const dateFilters = ['Today', '7 Days', '30 Days', 'This Quarter', 'Custom']

function App() {
  const [activeFilter, setActiveFilter] = useState('30 Days')
  const [currentPage, setCurrentPage] = useState('dashboard')

  return (
    <>
      <Sidebar onNavigate={setCurrentPage} currentPage={currentPage} />
      <div className="main-content">
        {currentPage === 'rateCapture' ? (
          <RateCapture onBack={() => setCurrentPage('dashboard')} />
        ) : (
          <>
            <TopBar />
            <div className="dashboard">
              <div className="date-filter">
                {dateFilters.map((f) => (
                  <button
                    key={f}
                    className={`date-btn ${activeFilter === f ? 'active' : ''}`}
                    onClick={() => setActiveFilter(f)}
                  >
                    {f}
                  </button>
                ))}
              </div>

              <KpiCards />

              <div className="charts-grid">
                <RevenueChart />
                <ConversionChart />
              </div>

              <OrdersTable />

              <div className="bottom-grid">
                <PaymentMethods />
                <RTOAnalytics />
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}

export default App
